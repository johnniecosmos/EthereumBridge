# import json
# from abc import abstractmethod
# from typing import Optional, Dict
#
#
# class ChainInterface:
#
#     def get_events_by_tx(self, tx_id: str) -> Optional[Dict]:
#         """ get logs for a tx with a key
#
#         :param tx_id: a valid hex string
#         """
#         raise NotImplementedError
#
#     def contract_tx(self, func_name: str, from_: str, private_key: bytes, *args):
#         """
#         Used for sending contract transactions (executing @func_name  on a ethr contract)
#         :param func_name: name of the function to invoke in the contract
#         :param from_: the account from which gas payment will be taken
#         :param private_key: private key matching the from_ account
#         :param args: see 'send_contract_tx' for more details
#         """
#         raise NotImplementedError
#
#     def contract_tx_as_bytes(self, fn_name: str, *args) -> bytes:
#         """
#         In order to invoke functions in contracts, one would we required to generate the raw tx message and pass
#         it as param to the call function. call signature: call(g, a, v, in, insize, out, outsize).
#         This function helps to generate the 'in' param of the 'call' func.
#         For more information, see: https://solidity.readthedocs.io/en/v0.5.3/assembly.html
#
#         Note:
#             - args order is important
#             - this might not be require for all contracts (it is required for gnosis MultiSigWallet)
#         """
#         raise NotImplementedError
#
#     @abstractmethod
#     def extract_addr(self, tx_log: Dict) -> str:
#         raise NotImplementedError
#
#     @abstractmethod
#     def extract_amount(self, tx_log: Dict) -> int:
#         raise NotImplementedError
#
#     @abstractmethod
#     def verify_destination(self, tx_log: Dict) -> bool:
#         raise NotImplementedError
#
#     @classmethod
#     @abstractmethod
#     def tracked_event(cls) -> str:
#         raise NotImplementedError
