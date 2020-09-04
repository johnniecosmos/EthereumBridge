from typing import List

from mongoengine import connect
from pytest import fixture

from src.signer import MultiSig
from tests.unit import config
from tests.utils.keys import get_key_multisig_addr


@fixture(scope="module")
def test_configuration():
    config.multisig_acc_addr = get_key_multisig_addr(f"ms{config.signatures_threshold}")
    return config


@fixture(scope="module")
def db(test_configuration):
    # init connection to db
    connection = connect(db=test_configuration.db_name)

    # handle cleanup, fresh db
    db = connection.get_database(test_configuration.db_name)
    for collection in db.list_collection_names():
        db.drop_collection(collection)


@fixture(scope="module")
def multisig_account(test_configuration):
    threshold = test_configuration.signatures_threshold
    return MultiSig(multisig_acc_addr=get_key_multisig_addr(f"ms{threshold}"),
                    signer_acc_name=f"ms{config.signatures_threshold}")


@fixture(scope="module")
def signer_accounts(test_configuration) -> List[MultiSig]:
    threshold = test_configuration.signatures_threshold
    res = []
    multig_acc_addr = get_key_multisig_addr(f"ms{threshold}")
    for i in range(1, threshold + 1):
        res.append(MultiSig(multig_acc_addr, f"t{i}"))
    return res
