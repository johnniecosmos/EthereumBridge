import json

from web3 import Web3

from src.contracts.ethereum.message import Message
from src.util.web3 import normalize_address, send_contract_tx


class Contract:
    """Container for contract relevant data"""

    def __init__(self, provider: Web3, contract_address: str, abi_path: str):
        self.abi = self.load_abi(abi_path)
        self.address = contract_address
        self.contract = provider.eth.contract(address=self.normalized_address(), abi=self.abi)
        self.provider = provider

    def normalized_address(self):
        return normalize_address(self.address)

    @staticmethod
    def load_abi(abi_path_: str) -> str:
        with open(abi_path_, "r") as f:
            return json.load(f)['abi']

    def contract_tx(self, func_name: str, from_: str, private_key: bytes, message: Message):
        """
        Used for sending contract transactions
        :param func_name: name of the function to invoke in the contract
        :param from_: the account from which gas payment will be taken
        :param private_key: private key matching the from_ account
        :param message: see 'send_contract_tx' for more details
        """
        send_contract_tx(self.provider, self.contract, func_name, from_, private_key, *message.args())

    def contract_tx_as_bytes(self, fn_name: str, *args):
        """
        In order to invoke functions in contracts, one would we required to generate the raw tx message and pass
        it as param to the call function. call signature: call(g, a, v, in, insize, out, outsize).
        This function helps to generate the 'in' param of the 'call' func.
        For more information, see: https://solidity.readthedocs.io/en/v0.5.3/assembly.html

        Note:
            - args order is important
            - this might not be require for all contracts (it is required for gnosis MultiSigWallet)
        """
        self.contract.encodeABI(fn_name=fn_name, args=[*args])
