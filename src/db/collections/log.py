from datetime import datetime

from mongoengine import Document, DateTimeField, StringField


class Logs(Document):
    creation = DateTimeField(default=datetime.now, required=True)
    log = StringField(required=True)
