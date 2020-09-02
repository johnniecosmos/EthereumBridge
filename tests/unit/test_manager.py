from time import sleep

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from tests.unit.conftest import swap_log, m


def test_handle(manager):
    """Verify addition of record in the DB for swap transaction"""

    # logic occurs at mock_manager initiation, here we simply validate
    assert ETHSwap.objects(tx_hash=swap_log.transactionHash.hex()).count() == 1


def test_run(manager):
    """Tests that manager updates """

    # Create signature in db
    doc = ETHSwap.objects(tx_hash=swap_log.transactionHash.hex()).get()
    for i in range(m-1):
        Signatures(tx_id=doc.id, signed_tx="tx signature", signer=f"test signer {i}").save()

    # make sure manager doesn't sing with less than m signatures
    sleep(6)  # give manager time to process the signatures (wakeup from sleep loop)
    assert ETHSwap.objects(tx_hash=swap_log.transactionHash.hex()).get().status == Status.SWAP_STATUS_UNSIGNED.value

    # Add the final signature to allow confirmation
    Signatures(tx_id=doc.id, signed_tx="tx signature", signer="test signer").save()
    sleep(6)  # give manager time to process the signatures (wakeup from sleep loop)
    assert ETHSwap.objects(tx_hash=swap_log.transactionHash.hex()).get().status == Status.SWAP_STATUS_SIGNED.value
