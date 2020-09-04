from time import sleep
from uuid import uuid4

from pytest import fixture

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from src.signer import MultiSig
from src.signer import Signer


@fixture(scope="module")
def signer(db, offline_data, web3_provider, contract, test_configuration):
    multisig_account = MultiSig(multisig_acc_addr=test_configuration.multisig_acc_addr,
                                signer_acc_name="t1")
    return Signer(web3_provider, multisig_account, contract)


def test_catch_up(signer, offline_data):
    # offline data writes new tx in db, and here we verify that signer is notified and signs them
    # Note: if signer is initialized before offline_data, the test will pass however, 'catchup' won't be used
    # as all new tx will be confirmed by the notification mechanisem.

    assert Signatures.objects(tx_id=offline_data.id, signer=signer.multisig.signer_acc_name).count() == 1


def test_db_notifications(signer, offline_data: ETHSwap):
    Signatures.objects(tx_id=offline_data.id, signer=signer.multisig.signer_acc_name).delete()

    # make a copy
    d = ETHSwap(tx_hash=offline_data.tx_hash, status=Status.SWAP_STATUS_UNSIGNED.value,
                unsigned_tx=offline_data.unsigned_tx)
    offline_data.delete()
    # save copy to invoke notification
    d.save()

    # Check notification processed
    sleep(0.5)  # give signer time to process notification from DB
    signed_tx = signer._sign_with_secret_cli(d.unsigned_tx)

    assert Signatures.objects(tx_id=d.id, signer=signer.multisig.signer_acc_name).get().signed_tx == signed_tx

    # Check notification process only Status.SWAP_STATUS_UNSIGNED
    d = ETHSwap(tx_hash=f"test hash {uuid4()}", status=Status.SWAP_STATUS_FAILED.value,
                unsigned_tx=d.unsigned_tx).save()

    sleep(0.5)
    assert Signatures.objects(tx_id=d.id, signer=signer.multisig.signer_acc_name).count() == 0
