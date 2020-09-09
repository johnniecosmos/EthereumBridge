from threading import Event, Thread
from typing import List

from src import config as temp_config
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.log import Logs
from src.db.collections.signatures import Signatures
from src.signer import MultiSig
from src.util.common import temp_file, temp_files
from src.util.exceptions import catch_and_log
from src.util.logger import get_logger
from src.util.secretcli import broadcast, multisign_tx


class Leader:
    """Broadcasts signed transactions Ethr <-> Scrt"""

    def __init__(self, multisig_: MultiSig, config=temp_config):
        self.multisig = multisig_
        self.config = config

        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)
        self.stop_event = Event()
        Thread(target=self.scan_swap).start()
        Thread(target=self.scan_burn).start()

    # TODO: Improve logic by separating 'catch_up' and 'signal' operations
    def scan_swap(self):
        """Looking """
        while not self.stop_event.is_set():
            for tx in ETHSwap.objects(status=Status.SWAP_STATUS_SIGNED.value):
                signatures = [signature.signed_tx for signature in Signatures.objects(tx_id=tx.id)]

                if len(signatures) < self.config.signatures_threshold:
                    Logs(log=f"Tried to sign tx {tx.id}, without enough signatures"
                             f" (required: {self.config.signatures_threshold}, have: {len(signatures)})")

                signed_tx, success = catch_and_log(self.logger, self._create_multisig, tx.unsigned_tx, signatures)
                if success and self._broadcast(signed_tx):
                    tx.status = Status.SWAP_STATUS_SUBMITTED.value
                    tx.save()

            self.stop_event.wait(self.config.default_sleep_time_interval)

    def scan_burn(self):
        pass

    def _create_multisig(self, unsigned_tx: str, signatures: List[str]) -> str:
        with temp_file(unsigned_tx) as unsigned_tx_path:
            with temp_files(signatures) as signed_tx_paths:
                return multisign_tx(unsigned_tx_path, self.multisig.signer_acc_name, *signed_tx_paths)

    def _broadcast(self, signed_tx) -> bool:
        success_index = 1
        with temp_file(signed_tx) as signed_tx_path:
            return catch_and_log(self.logger, broadcast, signed_tx_path)[success_index]
