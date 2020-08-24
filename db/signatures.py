from mongoengine import Document, StringField,ReferenceField
from db.signer import Signer
from db.eth_swap import ETHSwap


class Signatures(Document):
    singer = ReferenceField(Signer)
    tx_id = ReferenceField(ETHSwap)
    signed_tx = StringField
