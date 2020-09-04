import os
from time import sleep

from brownie import *
from pytest import fixture
from shutil import copy

from src.util.common import project_base_path
import tests.integration as integration_package

contracts_folder = os.path.join(project_base_path(), 'src', 'contracts')
brownie_project_folder = os.path.join(integration_package.__name__, 'brownie_project')


@fixture(scope="module")
def make_project():
    os.mkdir(brownie_project_folder)
    project.new(brownie_project_folder)  # init brownie project structure

    for contract in filter(lambda p: p.endswith(".sol"), os.listdir(contracts_folder)):
        copy(os.path.join(contracts_folder, contract), os.path.join(brownie_project_folder, 'contracts', contract))
    brownie_project = project.load(brownie_project_folder, name="Swap")  # load and compile copied contracts
    brownie_project.load_config()
    from brownie.project.Swap import *
    network.connect('development')  # connect to ganache cli
    accounts.add()

    yield brownie_project, web3

    # cleanup
    del brownie_project
    del project
    sleep(1)
    os.rmdir(brownie_project_folder)




