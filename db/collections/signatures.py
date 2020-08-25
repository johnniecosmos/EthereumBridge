from mongoengine import Document, StringField, ReferenceField

from db.collections.eth_swap import ETHSwap
from db.collections.signer import Signer


class Signatures(Document):
    # singer = ReferenceField(Signer, required=True)
    tx_id = ReferenceField(ETHSwap, required=True)
    signed_tx = StringField(required=True)
