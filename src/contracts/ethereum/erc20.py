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
        return int(tx_log.args._value)

    def verify_destination(self, tx_log) -> bool:
        # returns true if the ERC20 was sent to the MultiSigWallet (that's how token transfer is preformed)
        # noinspection PyProtectedMember
        return tx_log.args._to.lower() == self.multisig_wallet_addr.lower()

    # noinspection PyPep8Naming
    @staticmethod
    def decode_encodeAbi(data: bytes) -> Tuple[str, int]:
        """
        This functions takes a chunk of data encoded by web3 contract encodeAbi func and extracts the params from it.
        :param data: an encodeAbi result
        """
        method_id, dest, amount = data[:10], data[34:74], data[74:138]
        return '0x' + dest.decode(), int(amount, 16)  # convert amount from hex to decimal

    @classmethod
    def tracked_event(cls) -> str:
        return 'Transfer'

# b'0xa9059cbb000000000000000000000000e6ec7f8934f95e0ebbca62ad344e3892c96187eb0000000000000000000000000000000000000000000000000000000000000064'
# @combomethod
# def decode_function_input(self -> this is contract, data: HexStr) -> Tuple['ContractFunction', Dict[str, Any]]:
#     # type ignored b/c expects data arg to be HexBytes
#     data = HexBytes(data)  # type: ignore
#     selector, params = data[:4], data[4:]
#     func = self.get_function_by_selector(selector)
#
#     names = get_abi_input_names(func.abi)
#     types = get_abi_input_types(func.abi)
#
#     decoded = self.web3.codec.decode_abi(types, cast(HexBytes, params))
#     normalized = map_abi_data(BASE_RETURN_NORMALIZERS, types, decoded)
#
#     return func, dict(zip(names, normalized))
