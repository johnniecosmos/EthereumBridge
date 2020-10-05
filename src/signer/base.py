# import json
# from collections import namedtuple
# from threading import Event, Thread
# from time import sleep
# from typing import Dict
#
# from mongoengine import OperationError
# from web3 import Web3
#
# from src.contracts.ethereum.ethr_contract import EthereumContract
# from src.db.collections.eth_swap import Swap, Status
# from src.db.collections.signatures import Signatures
# from src.util.common import temp_file
# from src.util.config import Config
# from src.util.logger import get_logger
# from src.util.secretcli import sign_tx as secretcli_sign, decrypt
# from src.util.web3 import event_log
#
# SecretAccount = namedtuple('SecretAccount', ['address', 'name'])
#
#
# class BaseSigner:
#     def __init__(self, multisig: SecretAccount, config: Config):
#         self.logger = get_logger(db_name=config['db_name'],
#                                  logger_name=config.get('logger_name', self.__class__.__name__))
#
#     def run(self):
#         """Scans the db for unsigned swap tx and signs them"""
#         raise NotImplementedError
#
#     def _sign_tx(self, tx: Swap):
#         """
#         Makes sure that the tx is valid and signs it
#
#         :raises: ValueError
#         """
#         raise NotImplementedError
#
#     def _is_signed(self, tx: Swap) -> bool:
#         """ Returns True if tx was already signed, else False """
#         return Signatures.objects(tx_id=tx.id, signer=self.multisig.name).count() > 0
#
#     def _is_valid(self, tx: Swap) -> bool:
#         """Assert that the data in the unsigned_tx matches the tx on the chain"""
#         _, log = event_log(tx.src_tx_hash, [self.contract.tracked_event()], self.provider, self.contract.contract)
#
#         if not log:  # because for some reason event_log can return None???
#             return False
#
#         unsigned_tx = json.loads(tx.unsigned_tx)
#         try:
#             res = self._decrypt(unsigned_tx)
#
#             json_start_index = res.find('{')
#             json_end_index = res.rfind('}') + 1
#             decrypted_data = json.loads(res[json_start_index:json_end_index])
#             # assert decrypted_data['mint']['eth_tx_hash'] == log.transactionHash.hex()
#             assert int(decrypted_data['mint']['amount']) == self.contract.extract_amount(log)
#             assert decrypted_data['mint']['address'] == self.contract.extract_addr(log)
#         except AssertionError as e:
#             self.logger.error(f"Failed to validate tx data: {tx}. Error: {e}")
#             return False
#
#         return True
#
#     def _sign_with_secret_cli(self, unsigned_tx: str) -> str:
#         with temp_file(unsigned_tx) as unsigned_tx_path:
#             res = secretcli_sign(unsigned_tx_path, self.multisig.address, self.multisig.name)
#
#         return res
#
#     @staticmethod
#     def _decrypt(unsigned_tx: Dict):
#         msg = unsigned_tx['value']['msg'][0]['value']['msg']
#         return decrypt(msg)
