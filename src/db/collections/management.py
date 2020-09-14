from enum import Enum
from logging import Logger

from mongoengine import Document, IntField, DoesNotExist, MultipleObjectsReturned


class Management(Document):
    nonce = IntField(required=True)
    src = IntField(required=True)

    @classmethod
    def last_block(cls, src: int, logger: Logger):
        """
        Returns last processed contract tx sequence number
        :param src: string describing src network (i.e: scrt, eth)
        """
        try:
            doc = Management.objects.get(src=src)
        except DoesNotExist:
            doc = Management(nonce=-1, src=src).save()
        except MultipleObjectsReturned as e:  # Corrupted DB
            logger.critical(msg=f"DB collection corrupter.\n{e}")
            raise e

        return doc.nonce


class Source(Enum):
    eth = 1
    scrt = 2
