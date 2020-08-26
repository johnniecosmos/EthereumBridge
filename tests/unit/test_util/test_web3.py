from util.web3 import extract_tx_by_address, last_confirmable_block


def test_extract_tx_by_address(block, new_tx):
    assert new_tx == extract_tx_by_address(new_tx.to, block)[0]


def test_last_confirmable_block(websocket_provider):
    assert type(last_confirmable_block(websocket_provider)) == int  # sanity check

