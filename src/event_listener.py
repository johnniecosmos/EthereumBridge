from threading import Thread, Event
from time import sleep
from typing import List, Callable

from web3 import Web3

from src import config as temp_config
from src.contracts.contract import Contract
from src.util.web3 import last_confirmable_block, extract_tx_by_address


class EventListener:
    """Tracks the block-chain for new transactions on a given address"""

    def __init__(self, contract: Contract, provider: Web3, config=temp_config):
        self.provider = provider
        self.contract = contract
        self.config = config
        self.callbacks: List[Callable] = []

        self.stop_event = Event()
        Thread(target=self.run).start()

    def register(self, callback: Callable):
        self.callbacks.append(callback)

    def run(self):
        current_block = self.provider.eth.getBlock('latest')

        while not self.stop_event.is_set():
            # noinspection PyUnresolvedReferences
            if current_block.number > last_confirmable_block(self.provider, self.config.blocks_confirmation_required):
                self.stop_event.wait(5)
            else:
                transactions = extract_tx_by_address(self.contract.address, current_block)
                for tx in transactions:
                    for callback in self.callbacks:
                        callback(tx)

                current_block += 1
