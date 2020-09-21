import os

from typing import Tuple

from web3 import Web3

from src.contracts.ethereum.contract import Contract
from src.contracts.ethereum.message import Message
from src.util.common import project_base_path


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


class MultisigWallet(Contract):
    def __init__(self, provider: Web3, contract_address: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'multisig_wallet', 'MultiSigSwapWallet.json')
        super().__init__(provider, contract_address, abi_path)

    def submit_transaction(self, from_: str, private_key: bytes, message: Submit):
        self.contract_tx('submitTransaction', from_, private_key, message)

    def confirm_transaction(self, from_: str, private_key: bytes, message: Confirm):
        self.contract_tx('confirmTransaction', from_, private_key, message)
