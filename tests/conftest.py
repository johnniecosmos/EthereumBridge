from os import path
from typing import List

from mongoengine import connect
from pytest import fixture

import tests as tests_package
import tests.utils as utils_package
from src.signer import MultiSig
from src.util.common import module_dir
from tests import config
from tests.utils.keys import get_key_multisig_addr

utils_folder = module_dir(utils_package)
tests_folder = module_dir(tests_package)


@fixture(scope="module")
def test_configuration():
    config.multisig_acc_addr = get_key_multisig_addr(f"ms{config.signatures_threshold}")
    config.enclave_key = path.join(tests_folder, 'deployment', 'io-master-cert.der')
    config.secret_contract_address = config.multisig_acc_addr  # TODO: change once secret contract is deployed
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
    multisig_addr = get_key_multisig_addr(f"ms{threshold}")
    return MultiSig(multisig_acc_addr=multisig_addr, signer_acc_name=f"ms{config.signatures_threshold}")


@fixture(scope="module")
def signer_accounts(test_configuration) -> List[MultiSig]:
    """multisig accounts for signers"""
    threshold = test_configuration.signatures_threshold
    multig_acc_addr = get_key_multisig_addr(f"ms{threshold}")

    res = []
    for i in range(1, threshold + 1):
        res.append(MultiSig(multig_acc_addr, f"t{i}"))
    return res
