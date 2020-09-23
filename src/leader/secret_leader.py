from threading import Thread
from typing import List

from mongoengine import signals

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from src.singer.secret_signer import MultiSig
from src.util.common import temp_file, temp_files
from src.util.exceptions import catch_and_log
from src.util.logger import get_logger
from src.util.secretcli import broadcast, multisig_tx


class SecretLeader:
    """Broadcasts signed transactions Ethr -> Scrt"""

    def __init__(self, multisig_: MultiSig, config):
        self.multisig = multisig_
        self.config = config
        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)

        Thread(target=self._catch_up).start()
        signals.post_save.connect(self._swap_signal, sender=ETHSwap)

    def _catch_up(self):
        """ Scans the DB for signed swap tx at startup"""
        # Note: As Collection.objects() call is cached, there shouldn't be collisions with DB signals
        for tx in ETHSwap.objects(status=Status.SWAP_STATUS_SIGNED.value):
            self._handle_swap(tx)

    # noinspection PyUnusedLocal
    def _swap_signal(self, sender, document, **kwargs):
        """Callback function to handle db signals"""
        if not document.status == Status.SWAP_STATUS_SIGNED.value:
            return
        try:
            self._handle_swap(document)
        except Exception as e:
            self.logger.error(msg=e)

    def _handle_swap(self, tx: ETHSwap):
        # reacts to a swap event on smart contract (notified by db)
        signatures = [signature.signed_tx for signature in Signatures.objects(tx_id=tx.id)]
        if len(signatures) < self.config.signatures_threshold:  # sanity check
            self.logger.error(msg=f"Tried to sign tx {tx.id}, without enough signatures"
                                  f" (required: {self.config.signatures_threshold}, have: {len(signatures)})")
            return

        signed_tx, success = catch_and_log(self.logger, self._create_multisig, tx.unsigned_tx, signatures)
        if success and self._broadcast(signed_tx):
            tx.status = Status.SWAP_STATUS_SUBMITTED.value
            tx.save()

    def _create_multisig(self, unsigned_tx: str, signatures: List[str]) -> str:
        """Takes all the signatures of the signers from the db and generates the signed tx with them."""

        # creates temp-files containing the signatures, as the 'multisign' command requires files as input
        with temp_file(unsigned_tx) as unsigned_tx_path:
            with temp_files(signatures, self.logger) as signed_tx_paths:
                return multisig_tx(unsigned_tx_path, self.multisig.signer_acc_name, *signed_tx_paths)

    def _broadcast(self, signed_tx) -> bool:
        # Note: This operation costs Scrt
        success_index = 1
        # TODO: validate broadcast - problematic without update to the secret contract
        with temp_file(signed_tx) as signed_tx_path:
            # TODO: remove -b block and later confirm
            return catch_and_log(self.logger, broadcast, signed_tx_path)[success_index]
