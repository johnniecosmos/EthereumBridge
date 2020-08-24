from mongoengine import Document, StringField


class Signer(Document):
    addr: StringField(required=True)
    public_key: StringField(required=True)
