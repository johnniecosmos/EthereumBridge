from threading import Thread, Event
from typing import List

from hexbytes import HexBytes
from web3 import Web3

from config import manager_sleep_time_seconds
from contracts.contract import Contract
from db.collections.eth_swap import ETHSwap, Status
from db.collections.signatures import Signatures
from event_listener import EventListener
from util.exceptions import catch_and_log
from util.web3 import event_log, normalize_address


class Manager:
    """Accepts new swap events and manages the tx status in db"""
    # TODO: Add a configuration module, to replace all specific config imports.
    def __init__(self, event_listener: EventListener, contract: Contract, provider: Web3, multisig_threshold=2):
        self.contract = contract
        self.provider = provider

        self.multisig_threshold = multisig_threshold

        self.stop_signal = Event()

        event_listener.register(self._handle)
        Thread(target=self.run).start()

    def run(self):
        """Scans for signed transactions and updates status if multisig threshold achieved"""
        while not self.stop_signal.is_set():
            for transaction in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
                if Signatures.objects(tx_id=transaction.id).count() >= self.multisig_threshold:
                    transaction.status = Status.SWAP_STATUS_SIGNED.value
                    transaction.save()
            self.stop_signal.wait(manager_sleep_time_seconds)

    def _handle(self, transactions: List[any]):
        """Registers transaction to the db"""

        self._handle_swap_events(transactions)

    def _handle_swap_events(self, events: List[any]):
        """Extracts tx of event 'swap' and saves to db"""
        for event in events:
            log = event_log(tx_hash=event.hash, event='Swap', provider=self.provider, contract=self.contract.contract)
            recipient = HexBytes(log.args.to).hex()
            unsigned_tx, success = catch_and_log(self.contract.generate_unsigned_tx,
                                                 normalize_address(log.address),
                                                 recipient,
                                                 log.args.amount)
            if success:
                ETHSwap.save_web3_tx(log, unsigned_tx)
