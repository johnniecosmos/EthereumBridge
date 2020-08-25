from time import sleep

from db.collections.eth_swap import ETHSwap, Status
from db.collections.signatures import Signatures


def test_handle(mock_manager, swap_tx):
    assert ETHSwap.objects(tx_hash=swap_tx.transactionHash.hex()).count() == 1


def test_run(mock_manager, swap_tx):
    """Tests that manager updates """

    # Create signature on tx
    doc = ETHSwap.objects(tx_hash=swap_tx.transactionHash.hex()).get()
    for _ in range(2):
        Signatures(tx_id=doc.id, signed_tx="tx signature").save()

    sleep(6)  # give manager time to process the signatures (wakeup from sleep loop)
    assert ETHSwap.objects(tx_hash=swap_tx.transactionHash.hex()).get().status == Status.SWAP_STATUS_CONFIRMED.value
