import os
from typing import Tuple

from web3 import Web3

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.util.common import project_base_path, Token


class Erc20(EthereumContract):
    def __init__(self, provider: Web3, token: Token, multisig_address: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'ethereum', 'abi', 'IERC20.json')
        self.token = token
        super().__init__(provider, token.address, abi_path)

        self.dest_address = multisig_address

    def symbol(self):
        return self.token.name

    def extract_addr(self, tx_log) -> str:
        return tx_log.args.recipient.decode()

    def extract_amount(self, tx_log) -> int:
        # noinspection PyProtectedMember
        return int(tx_log.args._value)  # pylint: disable=protected-access

    def verify_destination(self, tx_log) -> bool:
        # returns true if the ERC20 was sent to the MultiSigWallet (that's how token transfer is preformed)
        # noinspection PyProtectedMember
        return tx_log.args._to.lower() == self.dest_address.lower()    # pylint: disable=protected-access

    # noinspection PyPep8Naming
    def get_params_from_data(self, data: bytes) -> Tuple[str, int]:
        """
        This functions takes a chunk of data encoded by web3 contract encodeAbi func and extracts the params from it.
        :param data: an encodeAbi result
        """
        result = self.contract.decode_function_input(data.hex())
        print(f'{result=}')
        if len(data) < 139:
            raise ValueError("Data in erc-20 transaction must be 139 bytes or more")
        _, dest, amount = data[:10], data[34:74], data[74:138]
        return '0x' + dest.decode(), int(amount, 16)  # convert amount from hex to decimal