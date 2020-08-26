from mongoengine import Document, IntField


# TODO: HALP, stupid name is stupid! Mr. code reviewer - be my hero.
class ModeratorData(Document):
    last_block = IntField(required=True)
