import os
from pathlib import Path
from shutil import rmtree
from subprocess import run, PIPE
from typing import List

from brownie import accounts
from pytest import fixture
from web3 import Web3

import src.contracts.ethereum as contracts_package
import tests.integration as integration_package
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.secret.secret_contract import change_admin
from src.event_listener import EventListener
from src.leader.ethr_leader import EthrLeader
from src.leader.secret_leader import SecretLeader
from src.manager import Manager
from src.singer.ehtr_signer import EthrSigner
from src.singer.secret_signer import SecretSigner
from src.util.common import module_dir
from src.util.web3 import normalize_address

contracts_folder = os.path.join(module_dir(contracts_package), 'sol')
brownie_project_folder = os.path.join(module_dir(integration_package), 'brownie_project')


@fixture(scope="module")
def ethr_signers(event_listener, web3_provider, multisig_wallet, configuration, ether_accounts) -> List[EthrSigner]:
    res = []

    # we will manually create the last signer in test_3
    for acc in ether_accounts[:-1]:
        private_key = acc.privateKey
        address = acc.address

        res.append(EthrSigner(event_listener, web3_provider, multisig_wallet, private_key, address, configuration))

    yield res
    rmtree(Path.joinpath(Path.home(), ".bridge_test"), ignore_errors=True)


@fixture(scope="module")
def scrt_signers(event_listener, scrt_signer_keys, web3_provider, multisig_wallet, configuration, ethr_signers) -> \
        List[SecretSigner]:
    signers: List[SecretSigner] = []
    for index, key in enumerate(scrt_signer_keys):
        s = SecretSigner(web3_provider, key, multisig_wallet, configuration)
        signers.append(s)

    return signers


@fixture(scope="module")
def multisig_wallet(web3_provider, configuration, ether_accounts):
    # erc20_contract is here only to deploy and update configuration, can be remove if not working with ERC20
    from brownie.project.IntegrationTests import MultiSigSwapWallet
    # normalize_accounts = [normalize_address(acc.address) for acc in ether_accounts]
    swap_contract = MultiSigSwapWallet.deploy([acc.address for acc in ether_accounts],
                                              configuration.signatures_threshold,
                                              {'from': accounts[0]})
    contract_address = str(swap_contract.address)
    return MultisigWallet(web3_provider, contract_address)


@fixture(scope="module")
def ether_accounts(web3_provider, configuration):
    res = []
    for _ in range(configuration.signatures_threshold):
        acc = web3_provider.eth.account.create()
        # account[0] is network.eth.coinbase
        web3_provider.eth.sendTransaction({'from': normalize_address(web3_provider.eth.accounts[0]),
                                           'to': normalize_address(acc.address),
                                           'value': 10000000000000000})
        res.append(acc)

    return res


@fixture(scope="module")
def web3_provider():
    # connect to local ganache node, started by brownie
    return Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))


@fixture(scope="module")
def manager(event_listener, multisig_wallet, multisig_account, configuration):
    manager = Manager(event_listener, multisig_wallet, multisig_account, configuration)
    yield manager
    manager.stop_signal.set()


@fixture(scope="module")
def ethr_leader(multisig_account, configuration, web3_provider, multisig_wallet, ether_accounts):
    private_key = ether_accounts[0].privateKey
    address = normalize_address(ether_accounts[0].address)
    leader = EthrLeader(web3_provider, multisig_wallet, private_key, address, configuration)
    yield leader
    leader.stop_event.set()


@fixture(scope="module")
def scrt_leader(multisig_account, configuration):
    change_admin_q = f"docker exec secretdev secretcli tx compute execute " \
                     f"{configuration.secret_contract_address}" \
                     f" '{change_admin(multisig_account.multisig_acc_addr)}' --from a -y"
    res = run(change_admin_q, shell=True, stdout=PIPE, stderr=PIPE)
    return SecretLeader(multisig_account, configuration)


@fixture(scope="module")
def event_listener(multisig_wallet, web3_provider, configuration):
    listener = EventListener(multisig_wallet, web3_provider, configuration)
    yield listener
    listener.stop_event.set()
