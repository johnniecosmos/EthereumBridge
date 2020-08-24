from mongoengine import Document, StringField, ReferenceField

from db.eth_swap import ETHSwap
from db.signer import Signer


class Signatures(Document):
    singer = ReferenceField(Signer)
    tx_id = ReferenceField(ETHSwap)
    signed_tx = StringField
