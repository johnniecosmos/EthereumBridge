import os

from web3 import Web3

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.ethereum.message import Submit, Confirm
from src.util.common import project_base_path


class MultisigWallet(EthereumContract):
    def __init__(self, provider: Web3, contract_address: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'ethereum', 'MultiSigSwapWallet.json')
        super().__init__(provider, contract_address, abi_path)

    def submit_transaction(self, from_: str, private_key: bytes, message: Submit):
        self.contract_tx('submitTransaction', from_, private_key, message)

    def confirm_transaction(self, from_: str, private_key: bytes, message: Confirm):
        self.contract_tx('confirmTransaction', from_, private_key, message)
