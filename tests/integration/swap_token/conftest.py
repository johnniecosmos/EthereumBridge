import json
import os
import subprocess
import string
import random
from pathlib import Path
from shutil import copy, rmtree
from time import sleep
from typing import List

from brownie import project, network, accounts
from pytest import fixture

from src.contracts.secret.secret_contract import change_admin
from src.leader.erc20.leader import ERC20Leader
from src.leader.secret20 import Secret20Leader
from src.signer.erc20.signer import ERC20Signer
from src.util.common import Token, SecretAccount
from src.util.config import Config
from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.event_listener import EthEventListener
from src.leader.secret20.manager import SecretManager
from src.signer.secret20 import Secret20Signer
from src.util.web3 import normalize_address
from tests.integration.conftest import contracts_folder, brownie_project_folder
from tests.utils.keys import get_viewing_key


def rand_str(n):
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for i in range(n))


@fixture(scope="module")
def make_project(db, configuration: Config):

    rmtree(brownie_project_folder, ignore_errors=True)

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
def setup(make_project, configuration: Config, erc20_token):
    configuration['mint_token'] = True
    configuration['token_contract_addr'] = erc20_token.address

    tx_data = {"admin": configuration['a_address'].decode(), "name": "Coin Name", "symbol": "ETHR", "decimals": 6,
               "initial_balances": []}
    cmd = f"docker exec secretdev secretcli tx compute instantiate 1 --label {rand_str(10)} '{json.dumps(tx_data)}'" \
          f" --from a -b block -y"
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    res = subprocess.run("secretcli query compute list-contract-by-code 1 | jq '.[-1].address'",
                         shell=True, stdout=subprocess.PIPE)
    configuration['secret_token_address'] = res.stdout.decode().strip()[1:-1]

    res = subprocess.run(f"secretcli q compute contract-hash {configuration['secret_contract_address']}",
                         shell=True, stdout=subprocess.PIPE).stdout.decode().strip()[2:]
    configuration['code_hash'] = res


    configuration['viewing_key'] = get_viewing_key(configuration['a_address'].decode(),
                                                configuration['secret_contract_address'])

    res = subprocess.run(f"secretcli q compute contract-hash {configuration['secret_contract_address']}",
                         shell=True, stdout=subprocess.PIPE).stdout.decode().strip()[2:]
    configuration['code_hash'] = res


@fixture(scope="module")
def erc20_token(make_project):
    from brownie.project.IntegrationTests import EIP20
    # solidity contract deploy params
    _initialAmount = 1000
    _tokenName = 'TN'
    _decimalUnits = 18
    _tokenSymbol = 'TS'

    erc20 = EIP20.deploy(_initialAmount, _tokenName, _decimalUnits, _tokenSymbol,
                         {'from': accounts[0]})
    yield Token(erc20.address, _tokenSymbol)


@fixture(scope="module")
def erc20_contract(multisig_wallet, web3_provider, erc20_token):
    yield Erc20(web3_provider, erc20_token, multisig_wallet.address)


@fixture(scope="module")
def scrt_leader(multisig_account: SecretAccount, erc20_contract, configuration: Config):
    # change_admin_q = f"docker exec secretdev secretcli tx compute execute " \
    #                  f"{configuration['secret_contract_address']}" \
    #                  f" '{change_admin(multisig_account.address)}' --from a -y"
    # _ = subprocess.run(change_admin_q, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    s20_contract = Token(configuration['secret_contract_address'], configuration['secret_contract_name'])
    leader = Secret20Leader(multisig_account, s20_contract, erc20_contract, configuration)
    yield leader
    leader.stop()


@fixture(scope="module")
def scrt_signers(scrt_accounts, erc20_contract, configuration) -> List[Secret20Signer]:
    signers: List[Secret20Signer] = []
    for account in scrt_accounts:
        s = Secret20Signer(erc20_contract, account, configuration)
        signers.append(s)

    yield signers

    for signer in signers:
        signer.stop()


@fixture(scope="module")
def ethr_leader(multisig_account, configuration: Config, web3_provider, erc20_token, multisig_wallet, ether_accounts):
    configuration['leader_key'] = ether_accounts[0].key
    configuration['leader_acc_addr'] = normalize_address(ether_accounts[0].address)
    configuration['eth_start_block'] = web3_provider.eth.blockNumber

    leader = ERC20Leader(multisig_wallet, erc20_token, configuration)
    leader.start()
    yield leader
    leader.stop()


@fixture(scope="module")
def ethr_signers(multisig_wallet, configuration: Config, ether_accounts, erc20_token) -> List[ERC20Signer]:
    res = []
    # we will manually create the last signer in test_3
    for acc in ether_accounts[:]:
        private_key = acc.key
        address = acc.address

        res.append(ERC20Signer(multisig_wallet, erc20_token, private_key, address, configuration))

    yield res

    for signer in res:
        signer.stop()
    rmtree(Path.joinpath(Path.home(), ".bridge_test"), ignore_errors=True)