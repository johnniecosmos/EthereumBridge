from enum import Enum
from typing import List

from mongoengine import Document, StringField, IntField

from util.web3 import unsigned_tx


class Status(Enum):
    SWAP_STATUS_UNSIGNED = 1
    SWAP_STATUS_SIGNED = 2
    SWAP_STATUS_SUBMITTED = 3  # Submitted to Secret
    SWAP_STATUS_CONFIRMED = 4
    SWAP_STATUS_FAILED = 5


class ETHSwap(Document):
    tx_hash = StringField(required=True)  # TODO: check unique + index
    status = IntField(required=True)
    unsigned_tx = StringField(required=True)

    @classmethod
    def save_web3_tx(cls, transactions: List):
        for tx in transactions:
            tx_hash = tx.hash.hex()
            if ETHSwap.objects(tx_hash=tx_hash).count() == 0:
                ETHSwap(tx_hash=tx_hash, status=Status.SWAP_STATUS_UNSIGNED.value, unsigned_tx=unsigned_tx()).save()
