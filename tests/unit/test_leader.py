from os import remove
from tempfile import NamedTemporaryFile
from time import sleep

from pytest import fixture

from src.contracts.secret_contract import tx_args
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from src.leader import Leader
from src.util.secretcli import create_unsigined_tx, sign_tx


@fixture(scope="module")
def mock_tx():
    res = dict()
    res['transactionHash'] = "0x52fa86d21bbec7a3085b6d9681ce58e2d1a1512211262f9346f2b06a16b4b183"
    return res


@fixture(scope="module")
def leader(test_configuration, multisig_account, db):
    leader = Leader(multisig_account, test_configuration)
    yield leader
    leader.stop_event.set()


def test_run(leader, signer_accounts, multisig_account, mock_tx, test_configuration):
    # Create mock tx and save it to DB
    unsigned_tx_args = tx_args(1, mock_tx['transactionHash'], signer_accounts[0].multisig_acc_addr)
    unsigned_tx = create_unsigined_tx(test_configuration.secret_contract_address, unsigned_tx_args,
                                      test_configuration.chain_id, test_configuration.enclave_key,
                                      test_configuration.enclave_hash, multisig_account.multisig_acc_addr)
    eth_swap = ETHSwap(tx_hash=mock_tx['transactionHash'], status=Status.SWAP_STATUS_UNSIGNED.value,
                       unsigned_tx=unsigned_tx).save()

    # Sign the mock tx created above
    f = NamedTemporaryFile(mode="w+", delete=False)
    f.write(unsigned_tx)
    f.close()

    for signer in signer_accounts:
        signed_tx = sign_tx(f.name, multisig_account.multisig_acc_addr, signer.signer_acc_name)
        Signatures(tx_id=eth_swap.id, signed_tx=signed_tx, signer=signer.signer_acc_name).save()

    remove(f.name)
    # Set tx status to signed
    eth_swap.status = Status.SWAP_STATUS_SIGNED.value
    eth_swap.save()

    # Give leader time to process the tx
    sleep(6)

    # Assert Leader processed the tx
    assert ETHSwap.objects(id=eth_swap.id).get().status == Status.SWAP_STATUS_SUBMITTED.value
