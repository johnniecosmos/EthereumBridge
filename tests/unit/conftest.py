from hexbytes import HexBytes
from mongoengine import connect
from pytest import fixture
from web3.datastructures import AttributeDict

from db.collections.eth_swap import ETHSwap, Status
from event_listener import EventListener
from manager import Manager
from moderator import Moderator
from signer import Signer
from tests.unit.config import db as test_db

from util.web3 import web3_provider

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

tx_2 = AttributeDict({
    'blockHash': HexBytes('0x38c335ccf8374fa0f92b0da0cc888616fd503f58ad1fa06fe20ecb2986669701'),
    'blockNumber': 500001,
    'from': '0x201354729f8d0f8b64e9a0c353c672C6a66B3857',
    'gas': 90000,
    'gasPrice': 20000000000,
    'hash': HexBytes('0x8c3ee756a51dee99b43d79e17a25f9791be7796bb1fcfea6a75839786267c28c'),
    'input': '0xe1fa8e844821981498b480c160559d8f6e45fd4d1e1242a149370b62b74747733bc31a8d',
    'nonce': 19469,
    'r': HexBytes('0xb2f27c551e1b6bc928bdf6044951405981412d722d82f2fbcff6c560159602a8'),
    's': HexBytes('0x3fc3f6e45a3cfc7885a287db591bd00063b9e0c15556a7cc59664ceec0ebe066'),
    'to': '0xd10e3Be2bc8f959Bc8C41CF65F60dE721cF89ADF',
    'transactionIndex': 0,
    'v': 41,
    'value': 0})


@fixture(scope="module")
def new_tx():
    return tx_2


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


@fixture(scope="module")
def moderator(db):
    return Moderator()


class MyMock:
    def __getattr__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return self


class IntegerMock(MyMock):
    def __call__(self, *args, **kwargs):
        return 42


class BlockMock(MyMock):
    transactions = [tx_2]


@fixture(scope="module")
def block():
    return BlockMock()


@fixture(scope="module")
def http_provider():
    raise NotImplementedError
    # return web3_provider("")


@fixture(scope="module")
def ipc_provider():
    raise NotImplementedError
    # return web3_provider("")


@fixture(scope="module")
def websocket_provider():
    return web3_provider("wss://ropsten.infura.io/ws/v3/e5314917699a499c8f3171828fac0b74")
