from web3 import Web3

from temp import abi as temp_abi
from util.web3 import normalize_address


# TODO: generate abi from solidity file
# TODO: deploy with script?
class Contract:
    def __init__(self, provider: Web3, contract_address, abi=temp_abi):
        self.contract = provider.eth.contract(address=contract_address, abi=abi)
        self.address = contract_address
        self.abi = abi

    def normalized(self):
        return normalize_address(self.address)
