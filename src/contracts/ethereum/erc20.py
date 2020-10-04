import os
from typing import Tuple

from web3 import Web3

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.util.common import project_base_path


class Erc20(EthereumContract):
    def __init__(self, provider: Web3, contract_address: str, multisig_wallet_addr: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'ethereum', 'abi', 'EIP20.json')
        super().__init__(provider, contract_address, abi_path)
        self.multisig_wallet_addr = multisig_wallet_addr

    def extract_addr(self, tx_log) -> str:
        return tx_log.args.recipient.decode()

    def extract_amount(self, tx_log) -> int:
        # noinspection PyProtectedMember
        return int(tx_log.args._value)  # pylint: disable=protected-access

    def verify_destination(self, tx_log) -> bool:
        # returns true if the ERC20 was sent to the MultiSigWallet (that's how token transfer is preformed)
        # noinspection PyProtectedMember
        return tx_log.args._to.lower() == self.multisig_wallet_addr.lower()    # pylint: disable=protected-access

    # noinspection PyPep8Naming
    @staticmethod
    def decode_encodeAbi(data: bytes) -> Tuple[str, int]:
        """
        This functions takes a chunk of data encoded by web3 contract encodeAbi func and extracts the params from it.
        :param data: an encodeAbi result
        """
        _, dest, amount = data[:10], data[34:74], data[74:138]
        return '0x' + dest.decode(), int(amount, 16)  # convert amount from hex to decimal

    @classmethod
    def tracked_event(cls) -> str:
        return 'Transfer'
