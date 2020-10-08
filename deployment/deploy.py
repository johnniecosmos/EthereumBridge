import os
from shutil import copy, rmtree
from web3 import Web3
from src.util.config import Config
from src.util.web3 import web3_provider
from solc import compile_source

from brownie import accounts, project

signer_accounts = ['0x0F7D74b1B4a6063e3245f7bF51d5f5B1b17874C0', '0x55810874c137605b96e9d2B76C3089fcC325ed5d',
                   '0x984C31d834d1F13CCb3458f4623dB21975FE4892', '0x552B5078a9044688F6044B147Eb2C8DFb538737e']

def main():

    cfg = Config()

    with open('src/contracts/ethereum/sol/MultiSigSwapWallet.sol', 'r') as f:
        contract_source_code = f.read()

    compiled_sol = compile_source(contract_source_code)  # Compiled source code
    contract_interface = compiled_sol['<stdin>:MultiSigSwapWallet']

    w3 = web3_provider(cfg['eth_node_address'])

    # Instantiate and deploy contract
    contract = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])

    # Get transaction hash from deployed contract
    tx_hash = contract.deploy(transaction={'from': w3.eth.accounts[0], 'gas': 410000})
