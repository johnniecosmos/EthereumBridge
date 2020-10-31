import json
from abc import abstractmethod
from typing import Optional, List

from web3 import Web3
from web3.datastructures import AttributeDict

from src.util.web3 import normalize_address, send_contract_tx, event_log


class EthereumContract:
    """Container for contract relevant data"""

    def __init__(self, provider: Web3, contract_address: str, abi_path: str):
        self.abi = self.load_abi(abi_path)
        self._address = contract_address
        self.contract = provider.eth.contract(address=normalize_address(self._address), abi=self.abi)
        self.provider = provider

    @property
    def address(self):
        return self._address

    @staticmethod
    def load_abi(abi_path_: str) -> str:
        with open(abi_path_, "r") as f:
            return json.load(f)['abi']

    def get_events_by_tx(self, tx_id: str) -> Optional[AttributeDict]:
        """ get logs for a tx with a key

        :param tx_id: a valid 32 byte hex string
        """
        _, log = event_log(tx_id, self.tracked_event(), self.provider, self.contract)

        if not log:  # because for some reason event_log can return None???
            return None
        return log

    def send_transaction(self, func_name: str, from_: str, private_key: bytes, gas, *args, gas_price=None):
        """
        Used for sending contract transactions (executing @func_name  on a ethr contract)
        :param func_name: name of the function to invoke in the contract
        :param from_: the account from which gas payment will be taken
        :param private_key: private key matching the from_ account
        :param args: see 'send_contract_tx' for more details
        """
        return send_contract_tx(self.contract, func_name, from_, private_key, gas, *args, gas_price=gas_price)

    def transaction_raw_bytes(self, fn_name: str, *args):
        """
        In order to invoke functions in contracts, one would we required to generate the raw tx message and pass
        it as param to the call function. call signature: call(g, a, v, in, insize, out, outsize).
        This function helps to generate the 'in' param of the 'call' func.
        For more information, see: https://solidity.readthedocs.io/en/v0.5.3/assembly.html

        Note:
            - args order is important
            - this might not be require for all contracts (it is required for gnosis MultiSigWallet)
        """
        return self.contract.encodeABI(fn_name=fn_name, args=[*args]).encode()

    @abstractmethod
    def extract_addr(self, tx_log: AttributeDict) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract_amount(self, tx_log: AttributeDict) -> int:
        raise NotImplementedError

    @abstractmethod
    def verify_destination(self, tx_log: AttributeDict) -> bool:
        raise NotImplementedError

    @classmethod
    def tracked_event(cls) -> List[str]:
        return ['']
