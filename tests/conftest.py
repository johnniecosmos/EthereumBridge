from os import path
from subprocess import run, PIPE
from typing import List

from mongoengine import connect
from pytest import fixture

import tests as tests_package
import tests.utils as utils_package
from src.singer.secret_signer import MultiSig
from src.util.common import module_dir
from tests import config
from tests.utils.keys import get_key_multisig_addr

utils_folder = module_dir(utils_package)
tests_folder = module_dir(tests_package)


@fixture(scope="module")
def configuration():
    # get address of account 'a' on docker
    a_address = run("docker exec secretdev secretcli keys show a | jq '.address'", shell=True, stdout=PIPE)
    config.a_address = a_address.stdout.decode().strip()[1:-1].encode()
    config.multisig_acc_addr = get_key_multisig_addr(f"ms{config.signatures_threshold}")
    config.enclave_key = path.join(tests_folder, 'deployment', 'io-master-cert.der')

    res = run("secretcli query compute list-contract-by-code 1 | jq '.[0].address'", shell=True, stdout=PIPE)
    config.secret_contract_address = res.stdout.decode().strip()[1:-1]

    res = run(f"secretcli q compute contract-hash {config.secret_contract_address}",
              shell=True, stdout=PIPE).stdout.decode().strip()[2:]
    config.code_hash = res

    return config


@fixture(scope="module")
def db(configuration):
    # init connection to db
    connection = connect(db=configuration.db_name)

    # handle cleanup, fresh db
    db = connection.get_database(configuration.db_name)
    for collection in db.list_collection_names():
        db.drop_collection(collection)


@fixture(scope="module")
def multisig_account(configuration):
    threshold = configuration.signatures_threshold
    multisig_addr = get_key_multisig_addr(f"ms{threshold}")
    return MultiSig(multisig_acc_addr=multisig_addr, signer_acc_name=f"ms{config.signatures_threshold}")


@fixture(scope="module")
def scrt_signer_keys(configuration) -> List[MultiSig]:
    """multisig accounts for signers"""
    threshold = configuration.signatures_threshold
    multisig_acc_addr = get_key_multisig_addr(f"ms{threshold}")

    res = []
    for i in range(1, threshold + 1):
        res.append(MultiSig(multisig_acc_addr, f"t{i}"))
    return res
