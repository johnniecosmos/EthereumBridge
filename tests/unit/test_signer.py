from time import sleep
from uuid import uuid4

from db.collections.eth_swap import ETHSwap, Status
from db.collections.signatures import Signatures


def test_catch_up(signer, offline_data):
    # offline data writes new tx in db, and here we verify that signer is notified and signs them
    # Note: if signer is initialized before offline_data, the test will passת however, 'catchup' won't be used
    # as all new tx will be confirmed by the notification mechanisem.
    for swap in offline_data:
        assert Signatures.objects(tx_id=swap.id, signed_tx=signer.enc_key).count() == 1


def test_db_notifications(signer):
    # Check notification processed
    d = ETHSwap(tx_hash=f"test hash {uuid4()}", status=Status.SWAP_STATUS_UNSIGNED.value,
                unsigned_tx="{test_key: test_value}").save()

    sleep(0.5)  # give signer time to process notification from DB
    assert Signatures.objects(tx_id=d.id, signed_tx=signer.enc_key).count() == 1

    # Check notification process only Status.SWAP_STATUS_UNSIGNED
    d = ETHSwap(tx_hash=f"test hash {uuid4()}", status=Status.SWAP_STATUS_SIGNED.value,
                unsigned_tx="{test_key: test_value}").save()

    sleep(0.5)
    assert Signatures.objects(tx_id=d.id, signed_tx=signer.enc_key).count() == 0
