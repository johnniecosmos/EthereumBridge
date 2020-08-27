from hexbytes import HexBytes
from mongoengine import connect
from pytest import fixture
from web3.datastructures import AttributeDict

import temp
from contracts.contract import Contract
from db.collections.eth_swap import ETHSwap, Status
from event_listener import EventListener
from manager import Manager
from moderator import Moderator
from signer import Signer
from tests.unit.config import db as test_db
from util.web3 import web3_provider


# (m of n)
m = 2
n = 3

swap_log = AttributeDict({
    'args': AttributeDict({'from': '0x53c22DBaFAFCcA28F6E2644b82eca5F8D66be96E', 'to': b'\x00\xaa\xff', 'amount': 5}),
    'event': 'Swap',
    'logIndex': 7,
    'transactionIndex': 9,
    'transactionHash': HexBytes('0x753d90e6784c57a8cf89ad9d1ab19627b51b7b40d883bd58aa528d411a3d0987'),
    'address': '0xFc4589c481538F29aD738a13dA49Af79d93ECb21',
    'blockHash': HexBytes('0x5ebb84b4e2d4a58561d9694864af7b239fcf4fb9d1aac0c8bb0b9642f67ea85b'),
    'blockNumber': 8554408})


contract_tx = AttributeDict({
    'blockHash': HexBytes('0x5ebb84b4e2d4a58561d9694864af7b239fcf4fb9d1aac0c8bb0b9642f67ea85b'),
    'blockNumber': 8554408, 'from': '0x53c22DBaFAFCcA28F6E2644b82eca5F8D66be96E',
    'gas': 25414,
    'gasPrice': 2000000000,
    'hash': HexBytes('0x753d90e6784c57a8cf89ad9d1ab19627b51b7b40d883bd58aa528d411a3d0987'),
    'input': '0xaf2b4aba000000000000000000000',
    'nonce': 11,
    'r': HexBytes('0x62a724f407cd7e9beeb73953f8021ceaae89249bbfd76cba59d915cbab5df332'),
    's': HexBytes('0x164a5011aefadeaa35bf13df22d6473fd13df0df7f1f52d633e456936dce7aea'),
    'to': '0xFc4589c481538F29aD738a13dA49Af79d93ECb21',
    'transactionIndex': 9,
    'v': 42,
    'value': 0})


@fixture(scope="module")
def websocket_provider():
    return web3_provider("wss://ropsten.infura.io/ws/v3/e5314917699a499c8f3171828fac0b74")


@fixture(scope="module")
def contract(websocket_provider):
    contract_address = "0xfc4589c481538f29ad738a13da49af79d93ecb21"
    abi = temp.abi
    return Contract(websocket_provider, contract_address, abi)


class MockEventListener(EventListener):
    def register(self, callback):
        callback([contract_tx])

    def run(self):
        return


@fixture(scope="module")
def event_listener(contract, websocket_provider):
    return MockEventListener(contract, websocket_provider)


@fixture(scope="module")
def db():
    # init connection to db
    connection = connect(db=test_db["name"])

    # handle cleanup, fresh db
    db = connection.get_database(test_db["name"])
    for collection in db.list_collection_names():
        db.drop_collection(collection)


@fixture(scope="module")
def manager(db):
    global m
    manager = Manager(event_listener, contract, websocket_provider, m)
    yield manager
    manager.stop_signal.set()


# Note: has to be above signer
@fixture(scope="module")
def offline_data(db):
    res = []
    for i in range(m):
        d = ETHSwap(tx_hash=f"test hash {i}", status=Status.SWAP_STATUS_UNSIGNED.value,
                    unsigned_tx=f"test_key_{i}: test_value_{i}").save()
        res.append(d)
    return res


@fixture(scope="module")
def signer(db, offline_data):
    return Signer(enc_key="Signer test encryption key")


class MyMock:
    def __getattr__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return self


class BlockMock(MyMock):
    transactions = [contract_tx]


@fixture(scope="module")
def block():
    return BlockMock()


@fixture(scope="module")
def moderator(db):
    return Moderator(contract, websocket_provider)

@fixture(scope="module")
def http_provider():
    raise NotImplementedError
    # return web3_provider("")


@fixture(scope="module")
def ipc_provider():
    raise NotImplementedError
    # return web3_provider("")
