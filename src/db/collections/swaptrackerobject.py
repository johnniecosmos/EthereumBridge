from mongoengine import Document, IntField, DoesNotExist, MultipleObjectsReturned, StringField


class SwapTrackerObject(Document):
    nonce = IntField(required=True)
    src = StringField(required=True, unique=True)

    @classmethod
    def last_processed(cls, src: str):
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
    def get_or_create(cls, src: str):
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

        return doc

    @classmethod
    def update_last_processed(cls, src: str, update_val: int):
        doc = cls.objects.get(src=src)
        doc.nonce = update_val
        doc.save()


# class Source(Enum):
#     ETH = 1
#     SCRT = 2
