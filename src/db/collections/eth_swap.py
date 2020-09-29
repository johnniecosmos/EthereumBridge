from datetime import datetime
from enum import Enum

from mongoengine import Document, StringField, IntField, DateTimeField


class Status(Enum):
    SWAP_STATUS_UNSIGNED = 1
    SWAP_STATUS_SIGNED = 2
    SWAP_STATUS_SUBMITTED = 3  # Submitted to Secret
    SWAP_STATUS_CONFIRMED = 4
    SWAP_STATUS_FAILED = 5


class ETHSwap(Document):
    tx_hash = StringField(required=True, unique=True)
    status = IntField(required=True)
    unsigned_tx = StringField(required=True)
    creation = DateTimeField(default=datetime.now, required=True)
    scrt_tx_hash = StringField(required=True, default='')
