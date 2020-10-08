import json
import os
import subprocess
import string
import random
from pathlib import Path
from shutil import copy, rmtree
from time import sleep
from typing import List

from brownie import project, network
from brownie.exceptions import ProjectAlreadyLoaded
from pytest import fixture

from src.contracts.ethereum.event_listener import EthEventListener
from src.contracts.secret.secret_contract import change_admin
from src.leader.eth.leader import EtherLeader
from src.leader.secret20 import Secret20Leader
from src.signer.eth.signer import EtherSigner
from src.signer.secret20.signer import SecretAccount, Secret20Signer
from src.util.common import Token
from src.util.config import Config
from src.util.web3 import normalize_address
from tests.integration.conftest import contracts_folder, brownie_project_folder
from tests.utils.keys import get_viewing_key


def rand_str(n):
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for i in range(n))


@fixture(scope="module")
def setup(make_project, configuration: Config):
    tx_data = {"admin": configuration['a_address'].decode(), "name": "Coin Name", "symbol": "ETHR", "decimals": 6,
               "initial_balances": []}

    cmd = f"docker exec secretdev secretcli tx compute instantiate 1 --label {rand_str(10)} '{json.dumps(tx_data)}'" \
          f" --from a -b block -y"
    _ = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    res = subprocess.run("secretcli query compute list-contract-by-code 1 | jq '.[-1].address'",
                         shell=True, stdout=subprocess.PIPE)
    configuration['secret_contract_address'] = res.stdout.decode().strip()[1:-1]
    configuration['viewing_key'] = get_viewing_key(configuration['a_address'].decode(), configuration['secret_contract_address'])

    res = subprocess.run(f"secretcli q compute contract-hash {configuration['secret_contract_address']}",
                         shell=True, stdout=subprocess.PIPE).stdout.decode().strip()[2:]
    configuration['code_hash'] = res


@fixture(scope="module")
def make_project(db, configuration: Config):

    rmtree(brownie_project_folder, ignore_errors=True)

    # init brownie project structure
    project.new(brownie_project_folder)
    brownie_contracts_folder = os.path.join(brownie_project_folder, 'contracts')

    multisig_contract = os.path.join(contracts_folder, 'MultiSigSwapWallet.sol')
    copy(multisig_contract, os.path.join(brownie_contracts_folder, 'MultiSigSwapWallet.sol'))

    # load and compile contracts to project
    try:
        brownie_project = project.load(brownie_project_folder, name="IntegrationTests")
        brownie_project.load_config()
    except ProjectAlreadyLoaded:
        pass
    # noinspection PyUnresolvedReferences
    network.connect('development')  # connect to ganache cli

    yield

    # cleanup
    del brownie_project
    sleep(1)
    rmtree(brownie_project_folder, ignore_errors=True)


@fixture(scope="module")
def event_listener(multisig_wallet, configuration: Config):
    listener = EthEventListener(multisig_wallet, configuration)
    yield listener
    listener.stop()


@fixture(scope="module")
def scrt_leader(multisig_account: SecretAccount, event_listener, multisig_wallet, configuration: Config):
    change_admin_q = f"docker exec secretdev secretcli tx compute execute " \
                     f"{configuration['secret_contract_address']}" \
                     f" '{change_admin(multisig_account.address)}' --from a -y"
    _ = subprocess.run(change_admin_q, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    s20_contract = Token(configuration['secret_contract_address'], configuration['secret_contract_name'])
    leader = Secret20Leader(multisig_account, s20_contract, multisig_wallet, configuration)
    yield leader
    leader.stop()


@fixture(scope="module")
def scrt_signers(scrt_accounts, multisig_wallet, configuration) -> List[Secret20Signer]:
    signers: List[Secret20Signer] = []
    for account in scrt_accounts:
        s = Secret20Signer(multisig_wallet, account, configuration)
        signers.append(s)

    yield signers

    for signer in signers:
        signer.stop()


@fixture(scope="module")
def ethr_leader(multisig_account, configuration: Config, web3_provider, multisig_wallet, ether_accounts):
    configuration['leader_key'] = ether_accounts[0].key
    configuration['leader_acc_addr'] = normalize_address(ether_accounts[0].address)
    configuration['eth_start_block'] = web3_provider.eth.blockNumber

    leader = EtherLeader(multisig_wallet, configuration)
    leader.start()
    yield leader
    leader.stop_event.set()


@fixture(scope="module")
def ethr_signers(multisig_wallet, configuration: Config, ether_accounts) -> List[EtherSigner]:
    res = []
    # we will manually create the last signer in test_3
    for acc in ether_accounts[:]:
        private_key = acc.key
        address = acc.address

        res.append(EtherSigner(multisig_wallet, private_key, address, configuration))

    yield res

    for signer in res:
        signer.stop()
    rmtree(Path.joinpath(Path.home(), ".bridge_test"), ignore_errors=True)
