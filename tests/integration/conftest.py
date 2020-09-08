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
from src.signer import Signer
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
    owners = [acc.address for acc in accounts[:test_configuration.signatures_threshold]]
    # account[0] is network.eth.coinbase
    swap_contract = MultiSigSwapWallet.deploy(owners, test_configuration.signatures_threshold,
                                              {'from': accounts[0]})

    yield brownie_project, swap_contract, network, accounts

    # cleanup
    del brownie_project
    sleep(1)
    rmtree(brownie_project_folder, ignore_errors=True)


@fixture(scope="module")
def brownie_project(make_project):
    p, _, _, _ = make_project
    return p


@fixture(scope="module")
def swap_contract(make_project):
    _, contract, _, _ = make_project
    return contract


@fixture(scope="module")
def brownie_network(make_project):
    _, _, net, _ = make_project
    return net


@fixture(scope="module")
def ganache_accounts(make_project):
    _, _, _, acc = make_project
    return acc


@fixture(scope="module")
def web3_provider(brownie_network):
    return brownie_network.web3


@fixture(scope="module")
def contract(web3_provider, swap_contract):
    contract_address = swap_contract.address
    return Contract(web3_provider, contract_address)


@fixture(scope="module")
def manager(event_listener, contract, web3_provider, multisig_account, test_configuration):
    manager = Manager(event_listener, contract, web3_provider, multisig_account, test_configuration)
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
def signers(signer_accounts, web3_provider, contract, test_configuration) -> List[Signer]:
    signers_: List[Signer] = []
    for i in signer_accounts:
        signers_.append(Signer(web3_provider, i, contract, test_configuration))
    return signers_


@fixture(scope="module")
def owners(test_configuration, make_project):
    return [acc.address for acc in accounts[:test_configuration.signatures_threshold]]
