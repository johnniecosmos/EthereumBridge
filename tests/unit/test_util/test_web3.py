from src.util.web3 import extract_tx_by_address
from tests.unit.conftest import contract_tx


def test_extract_tx_by_address(block):
    assert contract_tx == extract_tx_by_address(contract_tx.to, block)[0]
