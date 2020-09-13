from hexbytes import HexBytes
from pytest import fixture
from src.moderator import Moderator
from web3.datastructures import AttributeDict

from src.contracts.contract import Contract
from src.db.collections.eth_swap import ETHSwap, Status
from src.util.web3 import web3_provider, generate_unsigned_tx

swap_log = AttributeDict({
    'args': AttributeDict({'from': '0x53c22DBaFAFCcA28F6E2644b82eca5F8D66be96E', 'to': '0xabc123', 'amount': 5}),
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
def web3_provider():
    return web3_provider("wss://ropsten.infura.io/ws/v3/e5314917699a499c8f3171828fac0b74")


@fixture(scope="module")
def contract(web3_provider):
    contract_address = "0xfc4589c481538f29ad738a13da49af79d93ecb21"
    return Contract(web3_provider, contract_address)


# Note: has to be above signer
@fixture(scope="module")
def offline_data(db, test_configuration):
    unsigned_tx = generate_unsigned_tx(test_configuration.secret_contract_address, swap_log,
                                       test_configuration.chain_id, test_configuration.enclave_key,
                                       test_configuration.enclave_hash, test_configuration.multisig_acc_addr,
                                       )
    return ETHSwap(tx_hash=f"0xfc2ee006541030836591b7ebfb7bc7d5b233959f9d8df5ffdade7014782baeea",
                   status=Status.SWAP_STATUS_UNSIGNED.value,
                   unsigned_tx=unsigned_tx).save()


class BlockMock:
    transactions = [contract_tx]


@fixture(scope="module")
def block():
    return BlockMock()


@fixture(scope="module")
def moderator(db):
    return Moderator(contract, web3_provider)
