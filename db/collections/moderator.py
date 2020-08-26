from mongoengine import Document, IntField


class ModeratorData(Document):
    last_block = IntField(required=True)
