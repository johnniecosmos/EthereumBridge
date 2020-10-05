from datetime import datetime

from mongoengine import Document, StringField, ReferenceField, DateTimeField

from src.db.collections.eth_swap import Swap


class Signatures(Document):
    tx_id = ReferenceField(Swap, required=True)
    signed_tx = StringField(required=True)
    signer = StringField(required=True)
    creation = DateTimeField(default=datetime.now, required=True)
