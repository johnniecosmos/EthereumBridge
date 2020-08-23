import json

from web3 import Web3
from temp import abi, address
ifura_url = "https://mainnet.infura.io/v3/e5314917699a499c8f3171828fac0b74"
abi = json.loads(abi)
address = Web3.toChecksumAddress(address.lower())  # TODO: reduces safety, check workaround

web3 = Web3(Web3.HTTPProvider(ifura_url))
contract = web3.eth.contract(address=address, abi=abi)
# Won't work with Infura, more info at https://web3py.readthedocs.io/en/stable/filters.html#filtering
event_filter = contract.events.Swap.createFilter(fromBlock='latest')
if __name__ == "__main__":
    pass