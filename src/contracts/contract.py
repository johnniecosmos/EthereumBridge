import json
import os

from web3 import Web3

from src.util.common import project_base_path
from src.util.web3 import normalize_address


class Contract:
    """Container for contract relevant data"""

    def __init__(self, provider: Web3, contract_address: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'MultiSigSwapWallet.json')
        self.abi = self.load_abi(abi_path)
        self.address = contract_address
        self.contract = provider.eth.contract(address=self.normalized_address(), abi=self.abi)

    def normalized_address(self):
        return normalize_address(self.address)

    @staticmethod
    def load_abi(abi_path_: str) -> str:
        with open(abi_path_, "r") as f:
            return json.load(f)['abi']
