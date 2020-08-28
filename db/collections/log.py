from datetime import datetime

from mongoengine import Document, DateTimeField, StringField


class Logs(Document):
    creation = DateTimeField(required=True, default=datetime)
    log = StringField(required=True)
