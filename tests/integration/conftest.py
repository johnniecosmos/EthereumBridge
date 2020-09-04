import os
from time import sleep

from pytest import fixture
from shutil import copy, rmtree

from src.util.common import module_dir
import src.contracts as contracts_package
import tests.integration as integration_package
from brownie import project, network, accounts

contracts_folder = module_dir(contracts_package)
brownie_project_folder = os.path.join(module_dir(integration_package), 'brownie_project')


@fixture(scope="module")
def make_project():
    # init brownie project structure
    project.new(brownie_project_folder)

    # copy contracts to brownie contract folder
    for contract in filter(lambda p: p.endswith(".sol"), os.listdir(contracts_folder)):
        copy(os.path.join(contracts_folder, contract), os.path.join(brownie_project_folder, 'contracts', contract))

    # load and compile contracts to project
    brownie_project = project.load(brownie_project_folder, name="Swap")
    brownie_project.load_config()

    # noinspection PyUnresolvedReferences
    from brownie.project.Swap import EthSwap
    network.connect('development')  # connect to ganache cli  # TODO: Consider if network reset required
    # EthSwap.deploy("EthSwap Token", "EST", 18, 1e20, {'from': accounts[0]})
    swap_contract = EthSwap.deploy({'from': accounts[0]})

    yield brownie_project, swap_contract, network, accounts

    # cleanup
    del brownie_project
    sleep(1)
    rmtree(brownie_project_folder, ignore_errors=True)


def test(make_project):
    brownie_project, swap_contract, netowrk, accounts = make_project

    pass


