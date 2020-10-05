import json
from datetime import datetime
from threading import Thread, Event
from time import sleep
from typing import List

from mongoengine import OperationError

from src.db.collections.eth_swap import Swap, Status
from src.db.collections.signatures import Signatures
from src.signer.secret_signer import SecretAccount
from src.util.common import temp_file, temp_files
from src.util.logger import get_logger
from src.util.secretcli import broadcast, multisig_tx, query_tx
from src.util.config import Config


BROADCAST_VALIDATION_COOLDOWN = 60
SCRT_BLOCK_TIME = 7


class SecretLeader(Thread):
    """ Broadcasts signed Secret-20 minting tx after successful ETH or ERC20 swap event """

    def __init__(self, secret_multisig: SecretAccount, config: Config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.multisig_name = secret_multisig.name
        self.config = config
        self.logger = get_logger(db_name=self.config['db_name'],
                                 logger_name=config.get('logger_name', self.__class__.__name__))
        self.stop_event = Event()
        # Thread(target=self._catch_up).start()
        # signals.post_save.connect(self._swap_signal, sender=Swap)
        # signals.post_save.connect(self._broadcast_validation, sender=Swap)
        super().__init__(group=None, name="SecretLeader", target=self._scan_swap, **kwargs)

    def _catch_up(self):
        """ Scans the DB for signed swap tx at startup"""
        # Note: As Collection.objects() call is cached, there shouldn't be collisions with DB signals
        for tx in Swap.objects(status=Status.SWAP_STATUS_SIGNED):
            self._create_and_broadcast(tx)

    def run(self):
        self._scan_swap()

    def _scan_swap(self):
        while not self.stop_event.is_set():
            for tx in Swap.objects(status=Status.SWAP_STATUS_SIGNED):
                self._create_and_broadcast(tx)
                sleep(SCRT_BLOCK_TIME)
            for tx in Swap.objects(status=Status.SWAP_STATUS_SUBMITTED):
                self._broadcast_validation(tx)
        self.stop_event.wait(self.config['sleep_interval'])

    # def _swap_signal(self, _, document, **kwargs):  # pylint: disable=unused-argument
    #     """Callback function to handle db signals
    #
    #     **kwargs needs to be here even if unused, because this function gets passed arguments from mongo internals
    #     """
    #     if document.status == Status.SWAP_STATUS_SIGNED.value:
    #         self._create_and_broadcast(document)
        # pretty sure this can't actually fail, so this is unnecessary
        # try:

        # except Exception as e:
        #     self.logger.error(msg=e)

    def _create_and_broadcast(self, tx: Swap):
        # reacts to signed tx in the DB that are ready to be sent to scrt
        signatures = [signature.signed_tx for signature in Signatures.objects(tx_id=tx.id)]
        if len(signatures) < self.config['signatures_threshold']:  # sanity check
            self.logger.error(msg=f"Tried to sign tx {tx.id}, without enough signatures"
                                  f" (required: {self.config['signatures_threshold']}, have: {len(signatures)})")
            return

        try:
            signed_tx = self._create_multisig(tx.unsigned_tx, signatures)
            scrt_tx_hash = self._broadcast(signed_tx)
            tx.status = Status.SWAP_STATUS_SUBMITTED
            tx.dst_tx_hash = scrt_tx_hash
            tx.save()
        except (RuntimeError, OperationError) as e:
            self.logger.error(msg=f"Failed to create multisig and broadcast, error: {e}")

    def _create_multisig(self, unsigned_tx: str, signatures: List[str]) -> str:
        """Takes all the signatures of the signers from the db and generates the signed tx with them."""

        # creates temp-files containing the signatures, as the 'multisign' command requires files as input
        with temp_file(unsigned_tx) as unsigned_tx_path:
            with temp_files(signatures, self.logger) as signed_tx_paths:
                return multisig_tx(unsigned_tx_path, self.multisig_name, *signed_tx_paths)

    @staticmethod
    def _broadcast(signed_tx) -> str:
        # Note: This operation costs Scrt
        with temp_file(signed_tx) as signed_tx_path:
            return json.loads(broadcast(signed_tx_path))['txhash']

    def _broadcast_validation(self, document: Swap):  # pylint: disable=unused-argument
        """validation of submitted broadcast signed tx

        **kwargs needs to be here even if unused, because this function gets passed arguments from mongo internals
        """
        if not document.status == Status.SWAP_STATUS_SUBMITTED:
            return

        tx_hash = document.dst_tx_hash
        try:
            res = json.loads(query_tx(tx_hash))
            logs = json.loads(res["raw_log"])[0]
            if not logs.get('log', ''):
                document.update(status=Status.SWAP_STATUS_CONFIRMED)
            else:
                # maybe the block took a long time - we wait 60 seconds before we mark it as failed
                if (datetime.utcnow() - document.updated_on).total_seconds() < BROADCAST_VALIDATION_COOLDOWN:
                    return
                document.update(status=Status.SWAP_STATUS_FAILED)
                self.logger.critical(f"Failed confirming broadcast for tx: {document}")
        except (IndexError, json.JSONDecodeError, RuntimeError) as e:
            self.logger.critical(f"Failed confirming broadcast for tx: {document}. Error: {e}")
            # This can fail, but if it does we want to crash - this can lead to duplicate amounts and confusion
            # Better to just stop and make sure everything is kosher before continuing
            document.update(status=Status.SWAP_STATUS_FAILED)
