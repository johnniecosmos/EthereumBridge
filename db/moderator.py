from mongoengine import Document, IntField


class Moderator(Document):
    last_block = IntField
