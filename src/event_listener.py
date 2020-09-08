from collections import defaultdict
from threading import Thread, Event, Lock
from typing import List, Callable, Dict

from web3 import Web3

from src import config as temp_config
from src.contracts.contract import Contract
from src.util.web3 import last_confirmable_block, extract_tx_by_address, event_log


class EventListener:
    """Tracks the block-chain for new transactions on a given address"""

    def __init__(self, contract: Contract, provider: Web3, config=temp_config):
        self.provider = provider
        self.contract = contract
        self.config = config
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)

        self.lock = Lock()
        self.stop_event = Event()
        Thread(target=self.run).start()

    def register(self, callback: Callable, events: List[str]):
        """
        Allows registration to certain event of contract
        Note: events are case-sensitive

        :param callback: callback function that will be invoked upon event
        :param events: list of events the caller wants to register to
        """
        with self.lock:
            for event in events:
                self.callbacks[event].append(callback)

    def run(self):
        """Notify registered callbacks upon event occurrence"""
        current_block_num = self.provider.eth.getBlock('latest').number

        while not self.stop_event.is_set():
            if current_block_num > last_confirmable_block(self.provider, self.config.blocks_confirmation_required):
                self.stop_event.wait(self.config.default_sleep_time_interval)
                continue

            block = self.provider.eth.getBlock(current_block_num, full_transactions=True)
            transactions = extract_tx_by_address(self.contract.address, block)

            for tx in transactions:
                with self.lock:
                    for event in self.callbacks.keys():
                        log = event_log(tx_hash=tx.hash, event=event, provider=self.provider,
                                        contract=self.contract.contract)
                        if not log:
                            continue

                        for callback in self.callbacks[event]:
                            callback(log)

            current_block_num += 1
