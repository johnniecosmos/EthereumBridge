from src.util.web3 import extract_tx_by_address, last_confirmable_block
from tests.unit.conftest import contract_tx


def test_extract_tx_by_address(block):
    assert contract_tx == extract_tx_by_address(contract_tx.to, block)[0]


def test_last_confirmable_block(websocket_provider):
    assert type(last_confirmable_block(websocket_provider)) == int  # sanity check
