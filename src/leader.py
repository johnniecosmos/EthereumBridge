from threading import Event, Thread
from typing import List, Dict

from web3 import Web3

from src import config as temp_config
from src.contracts.contract import Contract
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.log import Logs
from src.db.collections.signatures import Signatures
from src.signers import MultiSig
from src.util.common import temp_file, temp_files
from src.util.exceptions import catch_and_log
from src.util.logger import get_logger
from src.util.secretcli import broadcast, multisign_tx


class Leader:
    """Broadcasts signed transactions Ethr <-> Scrt"""

    def __init__(self, provider: Web3, multisig_: MultiSig, contract: Contract, private_key, acc_addr,
                 config=temp_config):
        self.provider = provider
        self.multisig = multisig_
        self.config = config
        self.contract = contract
        self.private_key = private_key

        self.default_account = acc_addr

        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)
        self.stop_event = Event()
        Thread(target=self.scan_swap).start()
        # Thread(target=self.scan_burn).start()

    # TODO: Improve logic by separating 'catch_up' and 'signal' operations
    def scan_swap(self):
        """Looking """
        while not self.stop_event.is_set():
            for tx in ETHSwap.objects(status=Status.SWAP_STATUS_SIGNED.value):
                signatures = [signature.signed_tx for signature in Signatures.objects(tx_id=tx.id)]

                if len(signatures) < self.config.signatures_threshold:
                    Logs(log=f"Tried to sign tx {tx.id}, without enough signatures"
                             f" (required: {self.config.signatures_threshold}, have: {len(signatures)})")

                signed_tx, success = catch_and_log(self.logger, self._create_multisig, tx.unsigned_tx, signatures)
                if success and self._broadcast(signed_tx):
                    tx.status = Status.SWAP_STATUS_SUBMITTED.value
                    tx.save()

            self.stop_event.wait(self.config.default_sleep_time_interval)

    # TODO: DO
    def scan_burn(self):
        pass

    def _create_multisig(self, unsigned_tx: str, signatures: List[str]) -> str:
        with temp_file(unsigned_tx) as unsigned_tx_path:
            with temp_files(signatures, self.logger) as signed_tx_paths:
                return multisign_tx(unsigned_tx_path, self.multisig.signer_acc_name, *signed_tx_paths)

    def _broadcast(self, signed_tx) -> bool:
        success_index = 1
        with temp_file(signed_tx) as signed_tx_path:
            return catch_and_log(self.logger, broadcast, signed_tx_path)[success_index]

    def _submit_tx(self, tx_data: Dict[str, any]):
        # Note: This operation costs Ethr
        submission_tx = self.contract.contract.functions.submitTransaction(
            tx_data['dest'],
            tx_data['value'],
            tx_data['data']). \
            buildTransaction(
            {'chainId': self.provider.eth.chainId,
             'gasPrice': self.provider.eth.gasPrice,
             'nonce': self.provider.eth.getTransactionCount(self.default_account),
             'from': self.default_account
             })
        signed_txn = self.provider.eth.account.sign_transaction(submission_tx, private_key=self.private_key)
        self.provider.eth.sendRawTransaction(signed_txn.rawTransaction)
