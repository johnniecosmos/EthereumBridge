from datetime import datetime
from enum import Enum

from mongoengine import Document, StringField, IntField, DateTimeField, signals


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
    scrt_tx_hash = StringField(required=True, default='')
    created_on = DateTimeField(default=datetime.utcnow())
    updated_on = DateTimeField(default=datetime.utcnow())

    @classmethod
    def pre_save(cls, _, document, **kwargs):  # pylint: disable=unused-argument
        document.updated_on = datetime.now()


signals.pre_save.connect(ETHSwap.pre_save, sender=ETHSwap)
