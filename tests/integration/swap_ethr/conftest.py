import json
import os
import subprocess
from shutil import copy, rmtree
from time import sleep

from brownie import project, network
from pytest import fixture

from tests.integration.conftest import contracts_folder, brownie_project_folder
from tests.utils.keys import get_viewing_key


@fixture(scope="module")
def setup(make_project, configuration):
    tx_data = {"admin": configuration.a_address.decode(), "name": "Coin Name", "symbol": "ETHR", "decimals": 6,
               "initial_balances": []}
    cmd = f"docker exec secretdev secretcli tx compute instantiate 1 --label EthrSwap '{json.dumps(tx_data)}'" \
          f" --from a -b block -y"
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    res = subprocess.run("secretcli query compute list-contract-by-code 1 | jq '.[0].address'",
                         shell=True, stdout=subprocess.PIPE)
    configuration.secret_contract_address = res.stdout.decode().strip()[1:-1]
    configuration.viewing_key = get_viewing_key(configuration.a_address.decode(), configuration.secret_contract_address)


@fixture(scope="module")
def make_project(db, configuration):
    # init brownie project structure
    project.new(brownie_project_folder)
    brownie_contracts_folder = os.path.join(brownie_project_folder, 'contracts')

    multisig_contract = os.path.join(contracts_folder, 'MultiSigSwapWallet.sol')
    copy(multisig_contract, os.path.join(brownie_contracts_folder, 'MultiSigSwapWallet.sol'))

    # load and compile contracts to project
    brownie_project = project.load(brownie_project_folder, name="IntegrationTests")
    brownie_project.load_config()

    # noinspection PyUnresolvedReferences
    network.connect('development')  # connect to ganache cli

    yield

    # cleanup
    del brownie_project
    sleep(1)
    rmtree(brownie_project_folder, ignore_errors=True)
