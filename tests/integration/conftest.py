import os
from shutil import copy, rmtree
from time import sleep
from typing import List

from brownie import project, network, accounts
from pytest import fixture

import src.contracts as contracts_package
import tests.integration as integration_package
from src.contracts.contract import Contract
from src.event_listener import EventListener
from src.leader import Leader
from src.manager import Manager
from src.signers import Signer
from src.util.common import module_dir

contracts_folder = module_dir(contracts_package)
brownie_project_folder = os.path.join(module_dir(integration_package), 'brownie_project')


@fixture(scope="module")
def make_project(db, test_configuration):
    # init brownie project structure
    project.new(brownie_project_folder)

    # copy contracts to brownie contract folder
    for contract in filter(lambda p: p.endswith(".sol"), os.listdir(contracts_folder)):
        copy(os.path.join(contracts_folder, contract), os.path.join(brownie_project_folder, 'contracts', contract))

    # load and compile contracts to project
    brownie_project = project.load(brownie_project_folder, name="IntegrationTests")
    brownie_project.load_config()

    # noinspection PyUnresolvedReferences
    from brownie.project.IntegrationTests import MultiSigSwapWallet
    network.connect('development')  # connect to ganache cli

    # create signing ethr accounts
    web3_ = network.web3
    eth_signers = [web3_.eth.accounts.create() for _ in range(test_configuration.signatures_threshold)]
    owners = get_eth_signers_accounts(eth_signers, accounts)

    # account[0] is network.eth.coinbase
    swap_contract = MultiSigSwapWallet.deploy(owners, test_configuration.signatures_threshold,
                                              {'from': accounts[0]})

    yield brownie_project, swap_contract, network, accounts, eth_signers

    # cleanup
    del brownie_project
    sleep(1)
    rmtree(brownie_project_folder, ignore_errors=True)

def get_eth_signers_accounts(eth_signers : AttributeDict, accounts):
    res = []
    for signer in eth_signers:



@fixture(scope="module")
def brownie_project(make_project):
    p, _, _, _, _ = make_project
    return p


@fixture(scope="module")
def swap_contract(make_project):
    _, contract, _, _, _ = make_project
    return contract


@fixture(scope="module")
def brownie_network(make_project):
    _, _, net, _, _ = make_project
    return net


@fixture(scope="module")
def ganache_accounts(make_project):
    _, _, _, acc, _ = make_project
    return acc


@fixture(scope="module")
def ethr_signers(make_project):
    _, _, _, _, signers = make_project
    yield signers


@fixture(scope="module")
def web3_provider(brownie_network):
    return brownie_network.web3


@fixture(scope="module")
def contract(web3_provider, swap_contract):
    contract_address = swap_contract.address
    return Contract(web3_provider, contract_address)


@fixture(scope="module")
def manager(event_listener, contract, multisig_account, test_configuration):
    manager = Manager(event_listener, contract, multisig_account, test_configuration)
    yield manager
    manager.stop_signal.set()


@fixture(scope="module")
def leader(multisig_account, test_configuration):
    leader = Leader(multisig_account, test_configuration)
    yield leader
    leader.stop_event.set()


@fixture(scope="module")
def event_listener(contract, web3_provider, test_configuration):
    listener = EventListener(contract, web3_provider, test_configuration)
    yield listener
    listener.stop_event.set()


@fixture(scope="module")
def signers(event_listener, scrt_signer_accounts, web3_provider, contract, test_configuration, ethr_signers) -> List[Signer]:

    signers_: List[Signer] = []
    for index, signer_ in enumerate(scrt_signer_accounts):
        private_key = ethr_signers[index]['privateKey']
        acc_addr = ethr_signers[index]['address']
        s = Signer(event_listener, web3_provider, signer_, contract, test_configuration, private_key, acc_addr)
        signers_.append(s)

    return signers_


@fixture(scope="module")
def owners(test_configuration, make_project):
    return [acc.address for acc in accounts[:test_configuration.signatures_threshold]]
