from time import sleep
from typing import List, Tuple

import config
from db.collections.eth_swap import ETHSwap, Status
from db.collections.log import Logs
from db.collections.signatures import Signatures
from signer import multisig
from util.exceptions import catch_and_log
from util.secretcli import broadcast, multisin_tx


class Leader:
    """Tracks the DB for signed tx and send a broadcast msg to the secret network"""
    def __init__(self, multisig_: multisig):
        self.multisig = multisig_
        self.required_signatures = config.signatures_threshold
        self.run()

    def run(self):
        while True:
            for tx in ETHSwap.objects(status=Status.SWAP_STATUS_SIGNED.value):
                signatures = [signature.signed_tx for signature in Signatures(tx_id=tx.id)]

                if len(signatures) < self.required_signatures:
                    Logs(log=f"Tried to sign tx {tx.id}, without enough signatures"
                             f" (required: {self.required_signatures}, have: {len(signatures)}")

                signed_tx, success = self.create_multisig(signatures, tx.unsigned_tx)
                if success and self.broadcast(signed_tx):
                    tx.status = Status.SWAP_STATUS_SUBMITTED
                    tx.save()

            sleep(5.0)

    def create_multisig(self, signatures: List[str], unsigned_tx: str) -> Tuple[str, bool]:
        return catch_and_log(multisin_tx, self.multisig.signer_acc_name, unsigned_tx, tuple(signatures))

    @staticmethod
    def broadcast(signed_tx) -> bool:
        success_index = 1
        return catch_and_log(broadcast, signed_tx)[success_index]
