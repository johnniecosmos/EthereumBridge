from enum import Enum

from mongoengine import Document, StringField, IntField


class Status(Enum):
    SWAP_STATUS_UNSIGNED = 1
    SWAP_STATUS_SIGNED = 2
    SWAP_STATUS_SUBMITTED = 3  # Submitted to Secret
    SWAP_STATUS_CONFIRMED = 4
    SWAP_STATUS_FAILED = 5


class ETHSwap(Document):
    tx_hash = StringField(required=True)
    status = IntField(required=True)
    unsigned_tx = StringField(required=True)
