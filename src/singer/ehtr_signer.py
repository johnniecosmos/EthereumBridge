from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Thread, Lock
from typing import Dict

from web3 import Web3
from web3.datastructures import AttributeDict

import src.contracts.ethereum.message as message
from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.secret.secret_contract import swap_query_res
from src.event_listener import EventListener
from src.util.logger import get_logger
from src.util.secretcli import query_scrt_swap
from src.util.web3 import contract_event_in_range


class EthrSigner:
    """Verifies Secret swap tx and adds it's confirmation to the smart contract"""

    def __init__(self, event_listener: EventListener, provider: Web3, multisig_wallet: MultisigWallet,
                 private_key: bytes, acc_addr: str, config):
        self.provider = provider
        self.multisig_wallet = multisig_wallet
        self.private_key = private_key
        self.default_account = acc_addr
        self.config = config
        self.logger = get_logger(db_name=config.db_name, logger_name=config.db_name)

        self.submissions_lock = Lock()
        self.catch_up_complete = False
        self.file_db = self._create_file_db()

        self.mint_token: bool = self.config.mint_token
        if self.mint_token:
            self.token_contract = Erc20(provider, config.token_contract_addr, self.multisig_wallet.address)

        self.thread_pool = ThreadPoolExecutor()
        event_listener.register(self.handle_submission, ['Submission'], 0)
        Thread(target=self._submission_catch_up).start()

    def handle_submission(self, submission_event: AttributeDict):
        """ Validates submission event with scrt network and sends confirmation if valid """
        try:
            self._validated_and_confirm(submission_event)
        except Exception as e:
            self.logger.error(msg=f"{e}")

    def _create_file_db(self):
        file_path = Path.joinpath(Path.home(), self.config.app_data, 'submission_events')
        Path.joinpath(Path.home(), self.config.app_data).mkdir(parents=True, exist_ok=True)
        return open(file_path, "a+")

    # noinspection PyUnresolvedReferences
    def _validated_and_confirm(self, submission_event: AttributeDict):
        """Tries to validate the transaction corresponding to submission id on the smart contract,
        and confirms if valid"""

        transaction_id = submission_event.args.transactionId
        data = self._submission_data(transaction_id)
        with self.submissions_lock:
            if self.catch_up_complete:
                self._update_last_block_processed(submission_event.blockNumber)

            if not self._is_confirmed(transaction_id, data) and self._is_valid(data):
                self._confirm_transaction(transaction_id)

    def _submission_catch_up(self):
        """ Used to sync the signer with the chain after downtime, utilize local file to keep track of last processed
         block number.
        """
        from_block = self.file_db.read()
        from_block = int(from_block) if from_block else 0
        to_block = self.provider.eth.getBlock('latest').number

        with self.thread_pool as pool:
            for event in contract_event_in_range(self.logger, self.provider, self.multisig_wallet, 'Submission',
                                                 from_block, to_block):
                self._update_last_block_processed(event.blockNumber)
                pool.submit(self._validated_and_confirm, event)

        self.catch_up_complete = True

    def _update_last_block_processed(self, block_num: int):
        self.file_db.seek(0)
        self.file_db.write(str(block_num))
        self.file_db.truncate()
        self.file_db.flush()

    def _submission_data(self, transaction_id) -> Dict[str, any]:
        data = self.multisig_wallet.contract.functions.transactions(transaction_id).call()
        return {'dest': data[0], 'value': data[1], 'data': data[2], 'executed': data[3], 'nonce': data[4],
                'ethr_tx_hash': transaction_id}

    def _is_valid(self, submission_data: Dict[str, any]) -> bool:
        # lookup the tx hash in scrt, and validate it.
        nonce = submission_data['nonce']
        swap = query_scrt_swap(nonce, self.config.secret_contract_address, self.config.viewing_key)

        try:
            swap_data = swap_query_res(swap)
        except Exception as e:
            self.logger.critical(msg=f"Validation failed. Swap event:{swap}, Error: {e}")
            return False
        if self._check_tx_data(swap_data, submission_data):
            return True
        self.logger.info(msg=f"Validation failed. Swap event:{swap}")
        return False

    def _check_tx_data(self, swap_data: dict, submission_data: dict) -> bool:
        """
        This used to verify both uScrt <-> ether and uScrt <-> erc20 tx data
        :param swap_data: the data from scrt contract query
        :param submission_data: the data from the proposed tx on the smart contract
        """
        if not self.mint_token:  # swapping scrt for ethr
            return int(swap_data['amount']) == int(submission_data['value'])

        if int(submission_data['value']) != 0:  # sanity check
            self.logger.critical(msg=f"Trying to swap ethr while swap_token flag is true. "
                                     f"Tx: {swap_data['ethr_tx_hash']}")
            return False

        addr, amount = self.token_contract.decode_encodeAbi(submission_data['data'])
        return addr.lower() == swap_data['destination'].lower() and amount == int(swap_data['amount'])

    def _is_confirmed(self, transaction_id: int, submission_data: Dict[str, any]) -> bool:
        """Checks with the data on the contract if signer already added confirmation or if threshold already reached"""

        # check if already executed
        if submission_data['executed']:
            return True

        # check if signer already signed the tx
        if self.multisig_wallet.contract.functions.confirmations(transaction_id, self.default_account).call():
            return True

        return False

    def _confirm_transaction(self, submission_id: int):
        """
        Sign the transaction with the signer's private key and then broadcast
        Note: This operation costs gas
        """
        msg = message.Confirm(submission_id)
        tx_hash = self.multisig_wallet.confirm_transaction(self.default_account, self.private_key, msg)
        self.logger.info(msg=f"Signer: {self.default_account}, signed msg: {msg}, tx hash: {tx_hash}")
