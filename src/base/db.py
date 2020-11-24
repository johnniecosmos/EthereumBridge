from mongoengine import Document, StringField

from .common import Network
from src.db import EnumField


class TokenPair(Document):
    network = EnumField(Network, required=True)  # Network hosting the source coin
    coin_name = StringField(required=True)  # Name of the coin on that network
    coin_address = StringField(required=True, unique=True)  # Address of the coin on that network
    secret_coin_name = StringField(required=True)  # Name of the associated coin on the Secret Network
    secret_coin_address = StringField(required=True, unique=True)  # Address of the associated coin on the Secret Net.
