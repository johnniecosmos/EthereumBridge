import json
import os
from abc import abstractmethod
from typing import Tuple

from web3 import Web3

from src.util.common import project_base_path
from src.util.web3 import normalize_address, send_contract_tx


class Message:
    @abstractmethod
    def args(self) -> Tuple:
        """converts msg attributes into args tuple"""
        pass


class Submit(Message):
    def __init__(self, dest: str, amount: int, nonce: int, data=b""):
        self.dest = dest
        self.amount = amount
        self.nonce = nonce
        self.data = data

    def args(self) -> Tuple:
        return self.dest, self.amount, self.nonce, self.dest


class Confirm(Message):
    def __init__(self, submission_id: int):
        self.submission_id = submission_id

    def args(self):
        return (self.submission_id,)


class Contract:
    """Container for contract relevant data"""

    def __init__(self, provider: Web3, contract_address: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'MultiSigSwapWallet.json')
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

    def submit_transaction(self, from_: str, private_key: bytes, message: Submit):
        """
        Used for sending swap events from SecretNetwork to Ethereum
        :param from_: the account from which gas payment will be taken
        :param private_key: private key matching the from_ account
        :param message:
        """
        send_contract_tx(self.provider, self.contract, 'submitTransaction', from_, private_key, *message.args())

    def confirm_transaction(self, from_: str, private_key: bytes, message: Confirm):
        """Used for confirming tx on the smart contract"""
        send_contract_tx(self.provider, self.contract, 'confirmTransaction', from_, private_key, *message.args())
