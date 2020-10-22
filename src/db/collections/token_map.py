from enum import Enum, auto

from mongoengine import Document, IntField, DoesNotExist, MultipleObjectsReturned, StringField


class TokenRecord(Document):
    name = StringField(required=True)
    swap_address: StringField(required=True)
    swap_code_hash: StringField(required=True)
    token_address: StringField(required=True)


class TokenMapRecord(Document):
    src = StringField(required=True)
    src_network = StringField(required=True)
    swap_token = TokenRecord


class TokenPairing(Document):
    src_network = StringField(required=True)
    src_name = StringField(required=True)
    src_address = StringField(required=True)
    dst_network = StringField(required=True)
    dst_address = StringField(required=True)
    scrt_swap_code_hash = StringField(required=True)
