import json

from web3 import Web3

from src.util.web3 import normalize_address

abi_path = r"/home/guy/Workspace/dev/EthereumBridge/src/temp/MultiSigSwapWallet.json"

with open(abi_path, "r") as f:
    abi = json.load(f)['abi']


class Contract:
    abi = abi

    def __init__(self, provider: Web3, contract_address: str):
        self.address = contract_address

        self.contract = provider.eth.contract(address=self.normalized_address(), abi=self.abi)

    def normalized_address(self):
        return normalize_address(self.address)
