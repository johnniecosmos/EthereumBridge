import json
from os import path
from subprocess import run, PIPE
from typing import List

from mongoengine import connect
from pytest import fixture

import tests as tests_package
import tests.utils as utils_package
from src.signers import MultiSig
from src.util.common import module_dir
from tests import config
from tests.utils.keys import get_key_multisig_addr

utils_folder = module_dir(utils_package)
tests_folder = module_dir(tests_package)


def deploy_contract(test_configuration):
    # TODO :Remove after multisig swap work
    t1_addr = run("secretcli keys show t1 -a", shell=True, stdout=PIPE).stdout.decode()[:-1]
    init_q = {"admin": test_configuration.a_address.decode(),
              "name": "CoinName", "symbol": "SYMBL", "decimals": 6,
              "initial_balances": [{"address": t1_addr, "amount": "100"}]}
    print(run(f"docker exec secretdev secretcli tx compute instantiate 1 --label LABEL '{json.dumps(init_q)}'"
              f" --from a -b block -y", shell=True, stdout=PIPE).stdout.decode())


@fixture(scope="module")
def test_configuration():
    # get address of account 'a' on docker
    a_address = run("docker exec secretdev secretcli keys show a | jq '.address'", shell=True, stdout=PIPE)
    config.a_address = a_address.stdout.decode().strip()[1:-1].encode()
    deploy_contract(config)  # TODO: remove
    config.multisig_acc_addr = get_key_multisig_addr(f"ms{config.signatures_threshold}")
    config.enclave_key = path.join(tests_folder, 'deployment', 'io-master-cert.der')

    res = run("secretcli query compute list-contract-by-code 1 | jq '.[0].address'", shell=True, stdout=PIPE)
    config.secret_contract_address = res.stdout.decode().strip()[1:-1]

    res = run(f"secretcli q compute contract-hash {config.secret_contract_address}",
              shell=True, stdout=PIPE).stdout.decode().strip()[2:-1]
    config.code_hash = res


    # get view key
    json_q = '{"create_viewing_key": {"entropy": "random phrase"}}'
    view_key_tx_hash = run(f"docker exec secretdev secretcli tx compute execute {config.secret_contract_address} "
                           f"'{json_q}' --from {config.a_address.decode()} --gas 3000000 -b block -y | jq '.txhash'",
                           shell=True, stdout=PIPE)
    view_key_tx_hash = view_key_tx_hash.stdout.decode().strip()[1:-1]
    view_key = run(f"docker exec secretdev secretcli q compute tx {view_key_tx_hash} | jq '.output_log' | "
                   f"jq '.[0].attributes[1].value'", shell=True, stdout=PIPE).stdout.decode().strip()[1:-1]
    config.viewing_key = view_key

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
def scrt_signer_keys(test_configuration) -> List[MultiSig]:
    """multisig accounts for signers"""
    threshold = test_configuration.signatures_threshold
    multisig_acc_addr = get_key_multisig_addr(f"ms{threshold}")

    res = []
    for i in range(1, threshold + 1):
        res.append(MultiSig(multisig_acc_addr, f"t{i}"))
    return res
