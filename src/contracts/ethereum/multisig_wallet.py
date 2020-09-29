import os

from web3 import Web3

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.ethereum.message import Submit, Confirm
from src.util.common import project_base_path


class MultisigWallet(EthereumContract):
    def __init__(self, provider: Web3, contract_address: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'ethereum', 'abi', 'MultiSigSwapWallet.json')
        super().__init__(provider, contract_address, abi_path)

    def submit_transaction(self, from_: str, private_key: bytes, message: Submit):
        return self.contract_tx('submitTransaction', from_, private_key, message)

    def confirm_transaction(self, from_: str, private_key: bytes, message: Confirm):
        return self.contract_tx('confirmTransaction', from_, private_key, message)

    def extract_addr(self, tx_log) -> str:
        return tx_log.args.recipient.decode()

    def extract_amount(self, tx_log) -> int:
        return tx_log.args.value

    def verify_destination(self, tx_log) -> bool:
        # returns true if the Ethr was sent to the MultiSigWallet
        # noinspection PyProtectedMember
        return tx_log.address.lower() == self.address.lower()

    @classmethod
    def tracked_event(cls) -> str:
        return 'Swap'
