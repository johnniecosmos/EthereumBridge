from threading import Event, Thread
from typing import List

from mongoengine import signals
from web3 import Web3

from src.contracts.contract import Contract, Submit
from src.contracts.secret_contract import swap_query_res
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.management import Management, Source
from src.db.collections.signatures import Signatures
from src.signers import MultiSig
from src.util.common import temp_file, temp_files
from src.util.exceptions import catch_and_log
from src.util.logger import get_logger
from src.util.secretcli import broadcast, multisig_tx, query_scrt_swap


class SecretLeader:
    """Broadcasts signed transactions Ethr -> Scrt"""

    def __init__(self, multisig_: MultiSig, config):
        self.multisig = multisig_
        self.config = config
        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)

        Thread(target=self._catch_up).start()
        signals.post_save.connect(self._swap_signal, sender=ETHSwap)

    def _catch_up(self):
        """ Scans the DB for signed swap tx at startup"""
        # Note: As Collection.objects() call is cached, there shouldn't be collisions with DB signals
        for tx in ETHSwap.objects(status=Status.SWAP_STATUS_SIGNED.value):
            self._handle_swap(tx)

    # noinspection PyUnusedLocal
    def _swap_signal(self, sender, document, **kwargs):
        """Callback function to handle db signals"""
        if not document.status == Status.SWAP_STATUS_SIGNED.value:
            return
        try:
            self._handle_swap(document)
        except Exception as e:
            self.logger.error(msg=e)

    def _handle_swap(self, tx):
        signatures = [signature.signed_tx for signature in Signatures.objects(tx_id=tx.id)]
        if len(signatures) < self.config.signatures_threshold:
            self.logger.error(msg=f"Tried to sign tx {tx.id}, without enough signatures"
                                  f" (required: {self.config.signatures_threshold}, have: {len(signatures)})")
            return

        signed_tx, success = catch_and_log(self.logger, self._create_multisig, tx.unsigned_tx, signatures)
        if success and self._broadcast(signed_tx):
            tx.status = Status.SWAP_STATUS_SUBMITTED.value
            tx.save()

    def _create_multisig(self, unsigned_tx: str, signatures: List[str]) -> str:
        with temp_file(unsigned_tx) as unsigned_tx_path:
            with temp_files(signatures, self.logger) as signed_tx_paths:
                return multisig_tx(unsigned_tx_path, self.multisig.signer_acc_name, *signed_tx_paths)

    def _broadcast(self, signed_tx) -> bool:
        # Note: This operation costs Scrt
        success_index = 1
        # TODO: validate broadcast - problematic without update to the secret contract
        with temp_file(signed_tx) as signed_tx_path:
            return catch_and_log(self.logger, broadcast, signed_tx_path)[success_index]


class EthrLeader:
    """Broadcasts signed transactions Scrt -> Ethr"""

    def __init__(self, provider: Web3, contract: Contract, private_key, acc_addr, config):
        self.provider = provider
        self.config = config
        self.contract = contract
        self.private_key = private_key
        self.default_account = acc_addr
        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)
        self.stop_event = Event()

        Thread(target=self._scan_swap).start()

    def _scan_swap(self):
        """ Scans secret network contract for swap events """
        current_nonce = Management.last_processed(Source.scrt.value, self.logger)
        doc = Management.objects(nonce=current_nonce, src=Source.scrt.value).get()
        next_nonce = current_nonce + 1

        while not self.stop_event.is_set():
            swap_data, success = query_scrt_swap(self.logger, next_nonce, self.config.secret_contract_address,
                                                 self.config.viewing_key)
            if success:
                self._handle_swap(swap_data)
                doc.nonce = next_nonce
                doc.save()
                next_nonce += 1
                continue

            self.stop_event.wait(self.config.default_sleep_time_interval)

    def _handle_swap(self, swap_data: str):
        # Note: This operation costs Ethr
        try:
            swap_json = swap_query_res(swap_data)
            msg = Submit(swap_json['destination'], int(swap_json['amount']), int(swap_json['nonce']))
            self.contract.submit_transaction(self.default_account, self.private_key, msg)

        except Exception as e:
            # TODO: i think there should be some alert mechanism around this \ db log tracking
            self.logger.info(msg=f"Failed swap, transaction data: {swap_data}. Error: {e}")
