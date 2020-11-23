from mongoengine import Document, StringField, IntField


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
    src_network = StringField(required=True)  # Blockchain name
    src_coin = StringField(required=True)  # Token name
    src_address = StringField(required=True, unique=True)  # Smart contract address

    dst_network = StringField(required=True)
    dst_coin = StringField(required=True)
    dst_address = StringField(required=True, unique=True)

    decimals = IntField(required=True)
    name = StringField(required=True)
