from hexbytes import HexBytes
from mongoengine import connect
from pytest import fixture
from web3.datastructures import AttributeDict

from db.collections.eth_swap import ETHSwap, Status
from event_listener import EventListener
from manager import Manager
from signer import Signer
from tests.unit.config import db as test_db

tx = AttributeDict({
    'args': AttributeDict({
        'from': '0x53c22DBaFAFCcA28F6E2644b82eca5F8D66be96E',
        'to': b'\x00\xaa\xff', 'amount': 1}),
    'event': 'Swap',
    'logIndex': 5,
    'transactionIndex': 3,
    'transactionHash': HexBytes('0x52fa86d21bbec7a3085b6d9681ce58e2d1a1512211262f9346f2b06a16b4b183'),
    'address': '0xFc4589c481538F29aD738a13dA49Af79d93ECb21',
    'blockHash': HexBytes('0x19649a5e66cc4b02e3b0c3108feb02e54627d0c07876a92333874adf2794cfe8'),
    'blockNumber': 8554171})


@fixture(scope="module")
def swap_tx():
    return tx


class MockEventListener(EventListener):
    # noinspection PyMissingConstructor
    def __init__(self):
        pass

    def register(self, callback):
        callback([tx])


class MockManager(Manager):
    def __init__(self):
        super().__init__(event_listener=MockEventListener(), multisig_threshold=2)


@fixture(scope="module")
def db():
    # init connection to db
    res = connect(db=test_db["name"])

    # handle cleanup, fresh db
    db = res.get_database(test_db["name"])
    for collection in db.list_collection_names():
        db.drop_collection(collection)


@fixture(scope="module")
def mock_manager(db):
    m = MockManager()
    yield m
    m.stop_signal.set()


# Note: has to be above signer
@fixture(scope="module")
def offline_data(db):
    res = []
    for i in range(3):
        d = ETHSwap(tx_hash=f"test hash {i}", status=Status.SWAP_STATUS_UNSIGNED.value,
                    unsigned_tx=f"test_key_{i}: test_value_{i}").save()
        res.append(d)
    return res


@fixture(scope="module")
def signer(db, offline_data):
    return Signer(enc_key="Signer test encryption key")
