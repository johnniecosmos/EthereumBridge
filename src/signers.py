import json
from collections import namedtuple
from threading import Thread, Lock
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
from src.util.secretcli import sign_tx as secretcli_sign, decrypt
from src.util.web3 import event_log

MultiSig = namedtuple('MultiSig', ['multisig_acc_addr', 'signer_acc_name'])


class SecretSigner:
    """Verifies Ethereum tx in SWAP_STATUS_UNSIGNED and adds it's signature"""

    def __init__(self, provider: Web3, multisig_: MultiSig, contract: Contract, config):
        self.provider = provider
        self.multisig = multisig_
        self.contract = contract
        self.logger = get_logger(db_name=config.db_name, logger_name=config.db_name)

        signals.post_save.connect(self._tx_signal, sender=ETHSwap)

        Thread(target=self._catch_up).start()
        # Thread(target=self._submission_catch_up).start()

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
        log = event_log(tx.tx_hash, 'Swap', self.provider, self.contract.contract)
        unsigned_tx = json.loads(tx.unsigned_tx)
        try:
            res, success = catch_and_log(self.logger, self.decrypt, unsigned_tx)
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
    def decrypt(unsigned_tx: Dict):
        msg = unsigned_tx['value']['msg'][0]['value']['msg']
        return decrypt(msg)


class EthrSigner:
    """Verifies Secret burn tx and adds it's confirmation to the smart contract"""

    def __init__(self, event_listener: EventListener, provider: Web3, contract: Contract, private_key: bytes,
                 acc_addr: str, config):
        # TODO: acc_addr probably not required
        self.provider = provider
        self.contract = contract
        self.logger = get_logger(db_name=config.db_name, logger_name=config.db_name)
        self.private_key = private_key

        self.default_account = acc_addr
        # self.provider.eth.defaultAccount = self.default_account

        self.processed_submission_tx = set()
        self.submissions_lock = Lock()

        event_listener.register(self.handle_submission, ['Submission'])
        # Thread(target=self._submission_catch_up).start()

    def handle_submission(self,  submission_event: AttributeDict):
        """Validates submission event with scrt network and sends confirmation if valid"""
        self._validated_and_confirm(submission_event)

    # TODO: add starting point of the catch_up
    def _submission_catch_up(self):
        """Iterates over the 'transactions map' of the smart contract, add validates tx if required"""
        # iterate the map
        # for each one, call _approve_and_submit
        pass  # TODO

    def _validated_and_confirm(self, submission_event: AttributeDict):
        """Tries to validate the transaction corresponding to submission id on the smart contract,
        and confirms if valid"""

        transaction_id = submission_event.args.transactionId
        data = self._submission_data(transaction_id)
        with self.submissions_lock:
            if transaction_id in self.processed_submission_tx:
                return

            if not self._is_confirmed(transaction_id, data) and self._is_valid(data):
                self._confirm_transaction(transaction_id)

            self.processed_submission_tx.add(transaction_id)

    def _submission_data(self, transaction_id) -> Dict[str, any]:
        data = self.contract.contract.functions.transactions(transaction_id).call()
        return {'dest': data[0], 'value': data[1], 'data': data[2], 'executed': data[3]}

    def _is_valid(self, submission_data: Dict[str, any]) -> bool:
        # lookup the tx hash in scrt, and validate it.
        return True

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
