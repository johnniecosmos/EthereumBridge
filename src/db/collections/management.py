from enum import Enum

from mongoengine import Document, IntField, DoesNotExist, MultipleObjectsReturned


class Management(Document):
    nonce = IntField(required=True)
    src = IntField(required=True, unique=True)

    @classmethod
    def last_processed(cls, src: int):
        """
        Returns last processed contract tx sequence number
        :param src: int enum describing src network (i.e: secret20, eth)
        """

        try:
            doc = cls.objects.get(src=src)
        except DoesNotExist:
            doc = cls(nonce=-1, src=src).save()
        except MultipleObjectsReturned as e:  # Corrupted DB
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
