from enum import Enum
from logging import Logger
from threading import Lock

from mongoengine import Document, IntField, DoesNotExist, MultipleObjectsReturned


class Management(Document):
    nonce = IntField(required=True)
    src = IntField(required=True, unique=True)

    lock = Lock()  # TODO

    @classmethod
    def last_processed(cls, src: int, logger: Logger):
        """
        Returns last processed contract tx sequence number
        :param src: int enum describing src network (i.e: scrt, eth)
        """

        try:
            doc = cls.objects.get(src=src)
        except DoesNotExist:
            doc = cls(nonce=-1, src=src).save()
        except MultipleObjectsReturned as e:  # Corrupted DB
            logger.critical(msg=f"DB collection corrupter. Error: {e}")
            raise e

        return doc.nonce

    @classmethod
    def update_last_processed(cls, src: int, update_val: int):
        doc = cls.objects.get(src=src)
        doc.nonce = update_val
        doc.save()


class Source(Enum):
    eth = 1
    scrt = 2
