from threading import Thread, Event, Lock
from time import sleep
from typing import List, Callable, Dict

from web3 import Web3
from web3.exceptions import BlockNotFound

from src import config as temp_config
from src.contracts.contract import Contract
from src.util.web3 import extract_tx_by_address, event_log


class EventListener:
    """Tracks the block-chain for new transactions on a given address"""

    def __init__(self, contract: Contract, provider: Web3, config=temp_config):
        self.provider = provider
        self.contract = contract
        self.config = config
        self.callbacks = Callbacks()

        self.stop_event = Event()
        Thread(target=self.run).start()

    def register(self, callback: Callable, events: List[str], confirmations_required: int = 0):
        """
        Allows registration to certain event of contract.
        Note: events are case-sensitive

        :param callback: callback function that will be invoked upon event
        :param events: list of events the caller wants to register to
        :param confirmations_required: after how many confirmations to notify of the event
        """
        for event in events:
            self.callbacks.add(event, callback, confirmations_required)

    def run(self):
        """Notify registered callbacks upon event occurrence"""
        current_block_num = self.provider.eth.getBlock('latest').number

        while not self.stop_event.is_set():
            try:
                block = self.provider.eth.getBlock(current_block_num, full_transactions=True)
            except BlockNotFound:
                sleep(self.config.default_sleep_time_interval)
                continue

            self.callbacks.call(self.provider, self.contract, block.number)

            current_block_num += 1


class Callbacks:
    def __init__(self):
        self.callbacks_by_confirmations: Dict[int, Dict[str, List[Callable]]] = dict()
        self.lock = Lock()

    def add(self, event_name: str, callback: Callable, confirmations_required: int):
        with self.lock:
            callbacks = self.callbacks_by_confirmations.setdefault(confirmations_required, dict())
            callbacks = callbacks.setdefault(event_name, list())
            callbacks.append(callback)

    def call(self, provider: Web3, contract: Contract, block_number: int):
        """ call all the callbacks whose confirmation threshold reached """

        for threshold, val in self.callbacks_by_confirmations.items():
            if not block_number - threshold <= 0:
                continue

            block = provider.eth.getBlock(block_number - threshold, full_transactions=True)
            contract_transactions = extract_tx_by_address(contract.address, block)

            if not contract_transactions:
                continue

            # TODO: improve to o(n) run time by providing event_log list of events (will save calls to the ethr node)
            for event, callbacks in val.items():
                for tx in contract_transactions:
                    log = event_log(tx_hash=tx.hash, event=event, provider=provider, contract=contract.contract)

                    if not log:
                        continue

                    for callback in callbacks:
                        callback(log)
