from concurrent.futures import ThreadPoolExecutor
from json import JSONDecodeError
from pathlib import Path
from threading import Lock
from typing import Dict

from web3.datastructures import AttributeDict
import src.contracts.ethereum.message as message
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.secret.secret_contract import swap_query_res
from src.util.config import Config
from src.util.logger import get_logger
from src.util.secretcli import query_scrt_swap
from src.util.web3 import contract_event_in_range, web3_provider


class HistoricalEthSigner:  # pylint: disable=too-many-instance-attributes, too-many-arguments
    """
    Helper that runs through all the db, and checks that
    """

    def __init__(self, multisig_wallet: MultisigWallet, private_key: bytes, account: str, config: Config):
        # todo: simplify this, pylint is right
        self.provider = web3_provider(config['eth_node_address'])
        self.multisig_wallet = multisig_wallet
        self.private_key = private_key
        self.account = account
        self.config = config
        self.logger = get_logger(db_name=config['db_name'],
                                 logger_name=config.get('logger_name', f"{self.__class__.__name__}-{self.account[0:5]}"))

        self.submissions_lock = Lock()
        self.catch_up_complete = False
        self.cache = self._create_cache()

        self.thread_pool = ThreadPoolExecutor()
        # super().__init__(group=None, name=f"EthCatchUp-{self.account}", target=self.run, **kwargs)

    def sign_all_historical_swaps(self):
        self._submission_catch_up()

    def handle_submission(self, submission_event: AttributeDict):
        """ Validates submission event with secret20 network and sends confirmation if valid """
        self._validate_and_sign(submission_event)

    def _create_cache(self):
        # todo: db this shit
        directory = Path.joinpath(Path.home(), self.config['app_data'])
        directory.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
        file_path = Path.joinpath(directory, f'submission_events_{self.account[0:5]}')

        return open(file_path, "a+")

    # noinspection PyUnresolvedReferences
    def _validate_and_sign(self, submission_event: AttributeDict):
        """Tries to validate the transaction corresponding to submission id on the smart contract,
        confirms and signs if valid"""
        transaction_id = submission_event.args.transactionId
        self.logger.info(f'Got submission event with transaction id: {transaction_id}, checking status')
        data = self.multisig_wallet.submission_data(transaction_id)
        with self.submissions_lock:
            # todo: might want to move this to the end, in case we fail processing so we can retry?
            if self.catch_up_complete:
                self._update_last_block_processed(submission_event.blockNumber)
            if not self._is_confirmed(transaction_id, data):
                self.logger.info(f'Transaction {transaction_id} is missing approvals. Checking validity..')

                try:
                    if self._is_valid(data):
                        self.logger.info(f'Transaction {transaction_id} is valid. Signing & approving..')
                        self._approve_and_sign(transaction_id)
                    else:
                        self.logger.error(f'Failed to validate transaction: {data}')
                except ValueError as e:
                    self.logger.error(f"Error parsing secret-20 swap event {data}. Error: {e}")

    def _submission_catch_up(self):
        """ Used to sync the signer with the chain after downtime, utilize local file to keep track of last processed
         block number.
        """

        from_block = self._choose_starting_block()
        to_block = self.provider.eth.getBlock('latest').number
        self.logger.info(f'starting to catch up from {from_block} to {to_block}..')
        with self.thread_pool as pool:
            for event in contract_event_in_range(self.provider, self.multisig_wallet, 'Submission',
                                                 from_block, to_block):
                self.logger.info(f'Got new Submission event on block: {event.blockNumber}')
                self._update_last_block_processed(event.blockNumber)
                pool.submit(self._validate_and_sign, event)

        self.catch_up_complete = True
        self.logger.info('catch up complete')

    def _choose_starting_block(self) -> int:
        """Returns the block from which we start scanning Ethereum for new tx"""
        from_block = self.cache.read()
        if from_block:  # if we have a record, use it
            return int(from_block)
        return self.config.get('eth_signer_start_block', 0)

    def _update_last_block_processed(self, block_num: int):
        self.cache.seek(0)
        self.cache.write(str(block_num))
        self.cache.truncate()
        self.cache.flush()

    def _is_valid(self, submission_data: Dict[str, any]) -> bool:
        # lookup the tx hash in secret20, and validate it.
        nonce = submission_data['nonce']
        swap = query_scrt_swap(nonce, self.config['secret_contract_address'], self.config['viewing_key'])

        try:
            swap_data = swap_query_res(swap)
        except (AttributeError, JSONDecodeError) as e:
            raise ValueError from e
        if self._validate_tx_data(swap_data, submission_data):
            return True
        return False

    @staticmethod
    def _validate_tx_data(swap_data: dict, submission_data: dict) -> bool:
        """
        This used to verify secret-20 <-> ether tx data
        :param swap_data: the data from secret20 contract query
        :param submission_data: the data from the proposed tx on the smart contract
        """
        return int(swap_data['amount']) == int(submission_data['value'])

    def _is_confirmed(self, transaction_id: int, submission_data: Dict[str, any]) -> bool:
        """Checks with the data on the contract if signer already added confirmation or if threshold already reached"""

        # check if already executed
        if submission_data['executed']:
            return True

        # check if signer already signed the tx
        if self.multisig_wallet.contract.functions.confirmations(transaction_id, self.account).call():
            return True

        return False

    def _approve_and_sign(self, submission_id: int):
        """
        Sign the transaction with the signer's private key and then broadcast
        Note: This operation costs gas
        """
        msg = message.Confirm(submission_id)
        tx_hash = self.multisig_wallet.confirm_transaction(self.account, self.private_key, msg)
        self.logger.info(msg=f"Signed transaction - signer: {self.account}, signed msg: {msg}, "
                             f"tx hash: {tx_hash.hex()}")
