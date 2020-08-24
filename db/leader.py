from mongoengine import Document, StringField


class Leader(Document):
    hash = StringField
