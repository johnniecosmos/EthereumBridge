import os

from web3 import Web3

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.util.common import project_base_path


class Erc20(EthereumContract):
    def __init__(self, provider: Web3, contract_address: str):
        # TODO: update path
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'ethereum', 'MultiSigSwapWallet.json')
        super().__init__(provider, contract_address, abi_path)

    def extract_addr(self, tx_log) -> str:
        raise NotImplementedError

    def extract_amount(self, tx_log) -> int:
        raise NotImplementedError

    @classmethod
    def tracked_event(cls) -> str:
        return 'Transfer'
