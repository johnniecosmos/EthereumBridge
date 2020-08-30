import json

from web3 import Web3

from temp.temp import abi as temp_abi
from util.web3 import normalize_address


# TODO: generate abi from solidity file
# TODO: deploy with script?
class Contract:
    abi = temp_abi

    def __init__(self, provider: Web3, contract_address: str):
        self.address = contract_address
        self.contract = provider.eth.contract(address=self.normalized_address(), abi=self.abi)

    def normalized_address(self):
        return normalize_address(self.address)

    @classmethod
    def generate_unsigned_tx(cls, contract_addr: str = "0xabcdefg...", recipient: str = "0xABCDEFG...",
                             amount: int = 1):
        return json.dumps({"contract_addr": contract_addr, "recipient": recipient, "amount": amount})
