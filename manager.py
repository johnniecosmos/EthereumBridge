from threading import Thread, Event
from typing import List

from web3 import Web3

from config import manager_sleep_time_seconds
from contracts.contract import Contract
from db.collections.eth_swap import ETHSwap, Status
from db.collections.signatures import Signatures
from event_listener import EventListener
from util.web3 import event_logs


class Manager:
    """Responsible of accepting to new events and generating corresponding records in DB """

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
            log = event_logs(tx_hash=event.hash, event='Swap', provider=self.provider, contract=self.contract.contract)
            unsigned_tx = self.contract. \
                generate_unsigned_tx(self.contract.generate_unsigned_tx(log.to, log.recipient, log.value))

            ETHSwap.save_web3_tx(log, unsigned_tx)
