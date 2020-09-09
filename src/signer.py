import json
from collections import namedtuple
from threading import Thread, Lock
from typing import Dict

from mongoengine import signals
from web3 import Web3

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


class Signer:
    """Verifies Ethereum tx in SWAP_STATUS_UNSIGNED and adds it's signature"""

    def __init__(self, event_listener: EventListener, provider: Web3, multisig_: MultiSig, contract: Contract, config):
        self.provider = provider
        self.multisig = multisig_
        self.contract = contract
        self.logger = get_logger(db_name=config.db_name, logger_name=config.db_name)
        self.processed_submission_tx = set()

        self.submissions_lock = Lock()

        signals.post_save.connect(self._new_tx_signal, sender=ETHSwap)
        event_listener.register(self.handle_submission, ['Submission'])
        Thread(target=self._swap_catch_up).start()
        # Thread(target=self._submission_catch_up).start()

    def _swap_catch_up(self):
        """Scans the db for unsigned swap tx and signs them"""
        for tx in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
            try:
                self._sign_tx(tx)
            except Exception as e:
                self.logger.error(msg=e)

    # noinspection PyUnusedLocal
    def _new_tx_signal(self, sender, document, **kwargs):
        """Callback function to handle db signals"""
        if not document.status == Status.SWAP_STATUS_UNSIGNED.value:
            return
        try:
            self._sign_tx(document)
        except Exception as e:
            self.logger.error(msg=e)

    def _sign_tx(self, tx: ETHSwap):
        """Makes sure that the tx is valid and signs it"""
        if self._is_swap_signed(tx):
            self.logger.error(f"Tried to sign an already signed tx. Signer:\n"
                              f" {self.multisig.signer_acc_name}.\ntx id:{tx.id}.")
            return

        if not self._is_swap_valid(tx):
            self.logger.error(f"Validation failed. Signer:\n {self.multisig.signer_acc_name}.\ntx id:{tx.id}.")
            return

        # noinspection PyBroadException
        signed_tx, success = catch_and_log(self.logger, self._sign_with_secret_cli, tx.unsigned_tx)

        if success:
            Signatures(tx_id=tx.id, signer=self.multisig.signer_acc_name, signed_tx=signed_tx).save()

    def _is_swap_signed(self, tx: ETHSwap) -> bool:
        """ Returns True if tx was already signed, else False """
        return Signatures.objects(tx_id=tx.id, signer=self.multisig.signer_acc_name).count() > 0

    def _is_swap_valid(self, tx: ETHSwap) -> bool:
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

    def handle_submission(self,  submission_id: int):
        """Validates submission event with scrt network and sends confirmation if valid"""
        self._validated_and_confirm(submission_id)

    # TODO: add starting point of the catch_up
    def _submission_catch_up(self):
        """Iterates over the 'transactions map' of the smart contract, add validates tx if required"""
        # iterate the map
        # for each one, call _approve_and_submit

    def _validated_and_confirm(self, submission_id: int):
        """Tries to validate the transaction corresponding to submission id on the smart contract,
        and confirms if valid"""

        data = self._submission_data(submission_id)
        with self.submissions_lock:
            if not self._is_confirmed(submission_id) and self._is_submission_valid(data):
                self._confirm_transaction(data)

            self.processed_submission_tx.add(submission_id)

    def _submission_data(self, transaction_id) -> Dict[str, any]:
        temp = self.contract
        pass

    def _is_submission_valid(self, submission_data: Dict[str, any]) -> bool:
        # lookup the tx hash in scrt, and validate it.
        return True

    def _is_confirmed(self, submission_id: int) -> bool:
        """Checks with the data on the contract if signer already added confirmation or if threshold already reached"""
        temp = self.contract
        return False

    def _confirm_transaction(self, submission_data: Dict[str, any]) -> None:
        """
        Sends 'confirmTransaction' tx to the contract.
        Note: This operation costs gas
        """
        pass
