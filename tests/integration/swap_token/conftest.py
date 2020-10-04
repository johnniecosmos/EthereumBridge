import json
import os
import subprocess
from shutil import copy, rmtree
from time import sleep
from typing import List

from brownie import project, network, accounts
from pytest import fixture

from src.contracts.ethereum.erc20 import Erc20
from src.event_listener import EventListener
from src.manager import Manager
from src.singer.secret_signer import SecretSigner
from tests.integration.conftest import contracts_folder, brownie_project_folder
from tests.utils.keys import get_viewing_key


@fixture(scope="module")
def make_project(db, configuration):
    # init brownie project structure
    project.new(brownie_project_folder)

    # copy contracts to brownie contract folder
    brownie_contracts = os.path.join(brownie_project_folder, 'contracts')

    erc20_contract = os.path.join(contracts_folder, 'EIP20.sol')
    copy(erc20_contract, os.path.join(brownie_contracts, 'EIP20.sol'))

    multisig_contract = os.path.join(contracts_folder, 'MultiSigSwapWallet.sol')
    copy(multisig_contract, os.path.join(brownie_contracts, 'MultiSigSwapWallet.sol'))

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


@fixture(scope="module")
def setup(make_project, configuration, erc20_address):
    configuration.mint_token = True
    configuration.token_contract_addr = erc20_address

    tx_data = {"admin": configuration.a_address.decode(), "name": "Coin Name", "symbol": "ETHR", "decimals": 6,
               "initial_balances": []}
    cmd = f"docker exec secretdev secretcli tx compute instantiate 1 --label TokenSwap '{json.dumps(tx_data)}'" \
          f" --from a -b block -y"
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    res = subprocess.run("secretcli query compute list-contract-by-code 1 | jq '.[0].address'",
                         shell=True, stdout=subprocess.PIPE)
    configuration.secret_contract_address = res.stdout.decode().strip()[1:-1]
    configuration.viewing_key = get_viewing_key(configuration.a_address.decode(), configuration.secret_contract_address)

    res = subprocess.run(f"secretcli q compute contract-hash {configuration.secret_contract_address}",
                         shell=True, stdout=subprocess.PIPE).stdout.decode().strip()[2:]
    configuration.code_hash = res


@fixture(scope="module")
def erc20_address(make_project):
    from brownie.project.IntegrationTests import EIP20
    # solidity contract deploy params
    _initialAmount = 1000
    _tokenName = 'TN'
    _decimalUnits = 18
    _tokenSymbol = 'TS'

    erc20 = EIP20.deploy(_initialAmount, _tokenName, _decimalUnits, _tokenSymbol,
                         {'from': accounts[0]})
    yield str(erc20.address)


@fixture(scope="module")
def erc20_contract(multisig_wallet, web3_provider, erc20_address):
    yield Erc20(web3_provider, erc20_address, multisig_wallet.address)


@fixture(scope="module")
def event_listener_erc20(erc20_contract, web3_provider, configuration):
    listener = EventListener(erc20_contract, web3_provider, configuration)
    yield listener
    listener.stop_event.set()


@fixture(scope="module")
def manager(event_listener_erc20, erc20_contract, multisig_account, configuration):
    manager = Manager(event_listener_erc20, erc20_contract, multisig_account, configuration)
    yield manager
    manager.stop_signal.set()


@fixture(scope="module")
def scrt_signers(scrt_signer_keys, web3_provider, erc20_contract, configuration) -> List[SecretSigner]:
    signers: List[SecretSigner] = []
    for index, key in enumerate(scrt_signer_keys):
        s = SecretSigner(web3_provider, key, erc20_contract, configuration)
        signers.append(s)

    return signers
