import json

from web3 import Web3

from src.util.web3 import normalize_address

# TODO: move to config?
abi_path = r"/home/guy/Workspace/dev/EthereumBridge/src/contracts/MultiSigSwapWallet.json"


class Contract:
    """Container for contract relevant data"""
    def __init__(self, provider: Web3, contract_address: str):
        self.address = contract_address
        self.abi = self.load_abi(abi_path)
        self.contract = provider.eth.contract(address=self.normalized_address(), abi=self.abi)

    def normalized_address(self):
        return normalize_address(self.address)

    @staticmethod
    def load_abi(abi_path_: str) -> str:
        with open(abi_path_, "r") as f:
            return json.load(f)['abi']
