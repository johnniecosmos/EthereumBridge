from web3 import Web3

from src.temp.temp import abi as temp_abi
from src.util.web3 import normalize_address


# TODO: generate abi from solidity file
class Contract:
    abi = temp_abi

    def __init__(self, provider: Web3, contract_address: str):
        self.address = contract_address
        self.contract = provider.eth.contract(address=self.normalized_address(), abi=self.abi)

    def normalized_address(self):
        return normalize_address(self.address)
