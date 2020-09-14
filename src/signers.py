import json
from collections import namedtuple
from pathlib import Path
from threading import Thread, Lock, Event
from typing import Dict

from mongoengine import signals
from web3 import Web3
from web3.datastructures import AttributeDict

from src.contracts.contract import Contract
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from src.event_listener import EventListener
from src.util.common import temp_file
from src.util.exceptions import catch_and_log
from src.util.logger import get_logger
from src.util.secretcli import sign_tx as secretcli_sign, decrypt, query_burn
from src.util.web3 import event_log, contract_event_in_range

MultiSig = namedtuple('MultiSig', ['multisig_acc_addr', 'signer_acc_name'])


class SecretSigner:
    """Verifies Ethereum tx in SWAP_STATUS_UNSIGNED and adds it's signature"""

    def __init__(self, provider: Web3, multisig_: MultiSig, contract: Contract, config):
        self.provider = provider
        self.multisig = multisig_
        self.contract = contract
        self.config = config

        self.logger = get_logger(db_name=config.db_name, logger_name=config.db_name)

        signals.post_save.connect(self._tx_signal, sender=ETHSwap)

        Thread(target=self._catch_up).start()

    def _catch_up(self):
        """Scans the db for unsigned swap tx and signs them"""
        for tx in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
            try:
                self._sign_tx(tx)
            except Exception as e:
                self.logger.error(msg=e)

    # noinspection PyUnusedLocal
    def _tx_signal(self, sender, document, **kwargs):
        """Callback function to handle db signals"""
        if not document.status == Status.SWAP_STATUS_UNSIGNED.value:
            return
        try:
            self._sign_tx(document)
        except Exception as e:
            self.logger.error(msg=e)

    def _sign_tx(self, tx: ETHSwap):
        """Makes sure that the tx is valid and signs it"""
        if self._is_signed(tx):
            self.logger.error(f"Tried to sign an already signed tx. Signer:\n"
                              f" {self.multisig.signer_acc_name}.\ntx id:{tx.id}.")
            return

        if not self._is_valid(tx):
            self.logger.error(f"Validation failed. Signer:\n {self.multisig.signer_acc_name}.\ntx id:{tx.id}.")
            return

        # noinspection PyBroadException
        signed_tx, success = catch_and_log(self.logger, self._sign_with_secret_cli, tx.unsigned_tx)

        if success:
            Signatures(tx_id=tx.id, signer=self.multisig.signer_acc_name, signed_tx=signed_tx).save()

    def _is_signed(self, tx: ETHSwap) -> bool:
        """ Returns True if tx was already signed, else False """
        return Signatures.objects(tx_id=tx.id, signer=self.multisig.signer_acc_name).count() > 0

    def _is_valid(self, tx: ETHSwap) -> bool:
        """Assert that the data in the unsigned_tx matches the tx on the chain"""
        _, log = event_log(tx.tx_hash, ['Swap'], self.provider, self.contract.contract)
        unsigned_tx = json.loads(tx.unsigned_tx)
        try:
            res, success = catch_and_log(self.logger, self._decrypt, unsigned_tx)
            if not success:
                return False
            json_start_index = res.find('{')
            json_end_index = res.rfind('}') + 1
            decrypted_data = json.loads(res[json_start_index:json_end_index])
            assert decrypted_data['mint']['eth_tx_hash'] == log.transactionHash.hex()
            assert decrypted_data['mint']['amount_seth'] == log.args.value
            assert decrypted_data['mint']['to'] == log.args.recipient.decode()
        except AssertionError as e:
            self.logger.error(e)
            return False

        return True

    def _sign_with_secret_cli(self, unsigned_tx: str) -> str:
        with temp_file(unsigned_tx) as unsigned_tx_path:
            res = secretcli_sign(unsigned_tx_path, self.multisig.multisig_acc_addr, self.multisig.signer_acc_name)

        return res

    @staticmethod
    def _decrypt(unsigned_tx: Dict):
        msg = unsigned_tx['value']['msg'][0]['value']['msg']
        return decrypt(msg)


class EthrSigner:
    """Verifies Secret burn tx and adds it's confirmation to the smart contract"""

    def __init__(self, event_listener: EventListener, provider: Web3, contract: Contract, private_key: bytes,
                 acc_addr: str, config):
        self.provider = provider
        self.contract = contract
        self.private_key = private_key
        self.default_account = acc_addr
        self.config = config
        self.logger = get_logger(db_name=config.db_name, logger_name=config.db_name)

        # self.provider.eth.defaultAccount = self.default_account

        self.submissions_lock = Lock()

        self.catch_up_complete = Event()
        self.file_db = self._create_file_db()
        event_listener.register(self.handle_submission, ['Submission'])
        Thread(target=self._submission_catch_up).start()

    def handle_submission(self, submission_event: AttributeDict):
        """ Validates submission event with scrt network and sends confirmation if valid """
        self._validated_and_confirm(submission_event)

    def _create_file_db(self):
        file_path = Path.joinpath(Path.home(), self.config.app_data, 'submission_events')
        Path.joinpath(Path.home(), self.config.app_data).mkdir(parents=True, exist_ok=True)
        return open(file_path, "a+")

    def _submission_catch_up(self):
        """ Used to sync the signer with the chain after downtime, utilize local file to keep track of last processed
         block number.
        """
        from_block = self.file_db.read()
        from_block = int(from_block) if from_block else 0
        to_block = self.provider.eth.getBlock('latest').number - 1  # handle_submission starts from 'latest'

        for event in contract_event_in_range(self.logger, self.provider, self.contract, 'Submission', from_block,
                                             to_block):
            self._update_last_block_processed(event.blockNumber)
            Thread(target=self._validated_and_confirm, args=(event,)).start()

        self.catch_up_complete.set()

    # noinspection PyUnresolvedReferences
    def _validated_and_confirm(self, submission_event: AttributeDict):
        """Tries to validate the transaction corresponding to submission id on the smart contract,
        and confirms if valid"""

        transaction_id = submission_event.args.transactionId
        data = self._submission_data(transaction_id)
        with self.submissions_lock:
            if self.catch_up_complete.isSet():
                self._update_last_block_processed(submission_event.blockNumber)

            if not self._is_confirmed(transaction_id, data) and self._is_valid(data):
                self._confirm_transaction(transaction_id)

    def _update_last_block_processed(self, number: int):
        self.file_db.seek(0)
        self.file_db.write(str(number))
        self.file_db.truncate()
        self.file_db.flush()

    def _submission_data(self, transaction_id) -> Dict[str, any]:
        data = self.contract.contract.functions.transactions(transaction_id).call()
        return {'dest': data[0], 'value': data[1], 'data': json.loads(data[2]), 'executed': data[3]}

    def _is_valid(self, submission_data: Dict[str, any]) -> bool:
        # lookup the tx hash in scrt, and validate it.
        nonce = submission_data['data']['nonce']
        burn, success = catch_and_log(self.logger, query_burn, nonce,
                                      self.config.secret_contract_address, self.config.viewing_key)
        if success:
            try:
                burn_data = json.loads(burn)
            except Exception as e:
                self.logger.critical(msg=e)
                return False

            if burn_data['dest'].decode() == submission_data['dest'] \
                    and burn_data['value'] == submission_data['amount']:
                return True

        return False

    def _is_confirmed(self, transaction_id: int, submission_data: Dict[str, any]) -> bool:
        """Checks with the data on the contract if signer already added confirmation or if threshold already reached"""

        # check if already executed
        if submission_data['executed']:
            return True

        # check if signer already signed the tx
        if self.contract.contract.functions.confirmations(transaction_id, self.default_account).call():
            return True

        return False

    def _confirm_transaction(self, submission_id: int) -> None:
        """
        Sign the transaction with the signer's private key and then broadcast
        Note: This operation costs gas
        """
        submission_tx = self.contract.contract.functions.confirmTransaction(submission_id).buildTransaction(
            {'chainId': self.provider.eth.chainId,
             'gasPrice': self.provider.eth.gasPrice,
             'nonce': self.provider.eth.getTransactionCount(self.default_account),
             'from': self.default_account
             })
        signed_txn = self.provider.eth.account.sign_transaction(submission_tx, private_key=self.private_key)
        self.provider.eth.sendRawTransaction(signed_txn.rawTransaction)
