import json
from threading import Thread
from time import sleep
from typing import List

from mongoengine import signals

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from src.singer.secret_signer import MultiSig
from src.util.common import temp_file, temp_files
from src.util.logger import get_logger
from src.util.secretcli import broadcast, multisig_tx, query_tx


class SecretLeader:
    """Broadcasts signed transactions Ethr -> Scrt"""

    def __init__(self, multisig_: MultiSig, config):
        self.multisig = multisig_
        self.config = config
        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)

        Thread(target=self._catch_up).start()
        signals.post_save.connect(self._swap_signal, sender=ETHSwap)
        signals.post_save.connect(self._broadcast_validation, sender=ETHSwap)

    def _catch_up(self):
        """ Scans the DB for signed swap tx at startup"""
        # Note: As Collection.objects() call is cached, there shouldn't be collisions with DB signals
        for tx in ETHSwap.objects(status=Status.SWAP_STATUS_SIGNED.value):
            self._handle_swap(tx)

    def _swap_signal(self, sender, document, **kwargs):
        """Callback function to handle db signals"""
        if not document.status == Status.SWAP_STATUS_SIGNED.value:
            return
        try:
            self._handle_swap(document)
        except Exception as e:
            self.logger.error(msg=e)

    def _handle_swap(self, tx: ETHSwap):
        # reacts to signed tx in the DB that are ready to be sent to scrt
        signatures = [signature.signed_tx for signature in Signatures.objects(tx_id=tx.id)]
        if len(signatures) < self.config.signatures_threshold:  # sanity check
            self.logger.error(msg=f"Tried to sign tx {tx.id}, without enough signatures"
                                  f" (required: {self.config.signatures_threshold}, have: {len(signatures)})")
            return

        try:
            signed_tx = self._create_multisig(tx.unsigned_tx, signatures)
            scrt_tx_hash = self._broadcast(signed_tx)
            tx.status = Status.SWAP_STATUS_SUBMITTED.value
            tx.scrt_tx_hash = scrt_tx_hash
            tx.save()
        except RuntimeError as e:
            self.logger.error(msg=f"Failed to create multisig and broadcast, error: {e}")

    def _create_multisig(self, unsigned_tx: str, signatures: List[str]) -> str:
        """Takes all the signatures of the signers from the db and generates the signed tx with them."""

        # creates temp-files containing the signatures, as the 'multisign' command requires files as input
        with temp_file(unsigned_tx) as unsigned_tx_path:
            with temp_files(signatures, self.logger) as signed_tx_paths:
                return multisig_tx(unsigned_tx_path, self.multisig.signer_acc_name, *signed_tx_paths)

    @staticmethod
    def _broadcast(signed_tx) -> str:
        # Note: This operation costs Scrt
        with temp_file(signed_tx) as signed_tx_path:
            return json.loads(broadcast(signed_tx_path))['txhash']

    def _broadcast_validation(self, sender, document: ETHSwap, **kwargs):
        """validation of submitted broadcast signed tx """
        if not document.status == Status.SWAP_STATUS_SUBMITTED.value:
            return

        sleep(20)
        tx_hash = document.scrt_tx_hash
        try:
            res = json.loads(query_tx(tx_hash))
            logs = json.loads(res["raw_log"])[0]
            if not logs['log']:
                document.status = Status.SWAP_STATUS_CONFIRMED.value
            else:
                document.status = Status.SWAP_STATUS_FAILED.value
            document.save()
        except RuntimeError as e:
            self.logger.error(f"Failed confirming broadcast. Error: {e}")
            document.status = Status.SWAP_STATUS_FAILED
