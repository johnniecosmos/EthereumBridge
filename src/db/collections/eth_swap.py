from datetime import datetime
from enum import Enum, auto

from mongoengine import Document, StringField, DateTimeField, signals
from mongoengine.base import BaseField


class EnumField(BaseField):
    """
    A class to register Enum type (from the package enum34) into mongo
    :param choices: must be of :class:`enum.Enum`: type
        and will be used as possible choices
    """

    def __init__(self, enum, *args, **kwargs):
        self.enum = enum
        kwargs['choices'] = list(enum)
        super().__init__(*args, **kwargs)

    @staticmethod
    def __get_value(enum):
        return enum.value if hasattr(enum, 'value') else enum

    def to_python(self, value):
        return self.enum(super().to_python(value))

    def to_mongo(self, value):
        return self.__get_value(value)

    def prepare_query_value(self, op, value):
        return super().prepare_query_value(
                op, self.__get_value(value))

    def validate(self, value, clean=True):
        return super().validate(self.__get_value(value))

    def _validate(self, value, **kwargs):
        return super()._validate(
                self.enum(self.__get_value(value)), **kwargs)


class Status(Enum):
    SWAP_STATUS_UNSIGNED = auto()
    SWAP_STATUS_SIGNED = auto()
    SWAP_STATUS_SUBMITTED = auto()  # Submitted to Secret
    SWAP_STATUS_CONFIRMED = auto()
    SWAP_STATUS_FAILED = auto()


class Swap(Document):
    src_tx_hash = StringField(required=True, unique=True)
    src_network = StringField(required=True, default='eth')
    src_coin = StringField(required=True, default='eth')
    src_amount = StringField(required=True, default='')
    status = EnumField(Status, required=True)
    unsigned_tx = StringField(required=True)
    dst_tx_hash = StringField(required=True, default='')
    dst_network = StringField(required=True, default='secret20')
    dst_coin = StringField(required=True, default='seth')
    created_on = DateTimeField(default=datetime.utcnow())
    updated_on = DateTimeField(default=datetime.utcnow())

    @classmethod
    def pre_save(cls, _, document, **kwargs):  # pylint: disable=unused-argument
        document.updated_on = datetime.now()

    def __repr__(self):
        return f"<Swap hash {self.src_tx_hash} from {self.src_network} for {self.src_amount}{self.src_amount} " \
               f"to {self.dst_network} for {self.dst_coin}>"


signals.pre_save.connect(Swap.pre_save, sender=Swap)
