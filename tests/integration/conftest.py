import os
from pathlib import Path
from shutil import rmtree
from typing import List

from brownie import accounts
from pytest import fixture
from web3 import Web3

import src.contracts.ethereum as contracts_package
import tests.integration as integration_package
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.leader.eth.leader import EtherLeader
from src.signer.eth.signer import EtherSigner
from src.signer.secret20.signer import Secret20Signer
from src.util.common import module_dir
from src.util.config import Config
from src.util.web3 import normalize_address

contracts_folder = os.path.join(module_dir(contracts_package), 'sol')
brownie_project_folder = os.path.join(module_dir(integration_package), 'brownie_project')


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


@fixture(scope="module")
def multisig_wallet(web3_provider, configuration: Config, ether_accounts):
    # erc20_contract is here only to deploy and update configuration, can be remove if not working with ERC20
    from brownie.project.IntegrationTests import MultiSigSwapWallet
    # normalize_accounts = [normalize_address(acc.address) for acc in ether_accounts]
    swap_contract = MultiSigSwapWallet.deploy([acc.address for acc in ether_accounts],
                                              configuration['signatures_threshold'],
                                              {'from': accounts[0]})
    contract_address = str(swap_contract.address)
    return MultisigWallet(web3_provider, contract_address)


@fixture(scope="module")
def ether_accounts(web3_provider, configuration: Config):
    res = []
    for _ in range(configuration['signatures_threshold']):
        acc = web3_provider.eth.account.create()
        # account[0] is network.eth.coinbase
        web3_provider.eth.sendTransaction({'from': normalize_address(web3_provider.eth.accounts[0]),
                                           'to': normalize_address(acc.address),
                                           'value': 1000000000000000000})
        res.append(acc)

    return res


@fixture(scope="module")
def web3_provider(configuration):
    # connect to local ganache node, started by brownie
    return Web3(Web3.HTTPProvider(configuration['eth_node_address']))


@fixture(scope="module")
def ethr_leader(multisig_account, configuration: Config, web3_provider, multisig_wallet, ether_accounts):
    configuration['leader_key'] = ether_accounts[0].key
    configuration['leader_acc_addr'] = normalize_address(ether_accounts[0].address)
    configuration['eth_start_block'] = web3_provider.eth.blockNumber

    leader = EtherLeader(multisig_wallet, configuration)
    leader.start()
    yield leader
    leader.stop_event.set()

