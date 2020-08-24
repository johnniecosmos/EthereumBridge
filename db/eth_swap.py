from enum import Enum

from mongoengine import Document, StringField, IntField


class Status(Enum):
    SWAP_STATUS_UNSIGNED = 1
    SWAP_STATUS_SUBMITTED = 2
    SWAP_STATUS_CONFIRMED = 3
    SWAP_STATUS_FAILED = 4


class ETHSwap(Document):
    tx_hash = StringField(required=True)
    signer = StringField(required=True)
    status = IntField(required=True)
    unsigined_tx = StringField(required=True)
