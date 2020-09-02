from threading import Event
from typing import List, Tuple

from src import config
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.log import Logs
from src.db.collections.signatures import Signatures
from src.signer import MultiSig
from src.util.exceptions import catch_and_log
from src.util.secretcli import broadcast, multisign_tx


class Leader:
    """Tracks the DB for signed tx and send a broadcast tx to the secret network"""
    def __init__(self, multisig_: MultiSig):
        self.multisig = multisig_
        self.config = config
        self.run()
        self.stop_event = Event()

    def run(self):
        while not self.stop_event:
            for tx in ETHSwap.objects(status=Status.SWAP_STATUS_SIGNED.value):
                signatures = [signature.signed_tx for signature in Signatures(tx_id=tx.id)]

                if len(signatures) < self.config.signatures_threshold:
                    Logs(log=f"Tried to sign tx {tx.id}, without enough signatures"
                             f" (required: {self.config.signatures_threshold}, have: {len(signatures)})")

                signed_tx, success = self.create_multisig(signatures, tx.unsigned_tx)
                if success and self.broadcast(signed_tx):
                    tx.status = Status.SWAP_STATUS_SUBMITTED
                    tx.save()

            self.stop_event.wait(self.config.default_sleep_time_interval)

    def create_multisig(self, signatures: List[str], unsigned_tx: str) -> Tuple[str, bool]:
        return catch_and_log(multisign_tx, self.multisig.signer_acc_name, unsigned_tx, tuple(signatures))

    @staticmethod
    def broadcast(signed_tx) -> bool:
        success_index = 1
        return catch_and_log(broadcast, signed_tx)[success_index]
