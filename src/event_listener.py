from threading import Thread
from time import sleep
from typing import List, Callable

from web3 import Web3

from src import config
from src.contracts.contract import Contract
from src.util.web3 import last_confirmable_block, extract_tx_by_address


class EventListener:
    """Tracks the block-chain for new transactions on a given address"""

    def __init__(self, contract: Contract, provider: Web3):
        self.provider = provider
        self.contract = contract

        self.callbacks: List[Callable] = []

        Thread(target=self.run).start()

    def register(self, callback: Callable):
        self.callbacks.append(callback)

    def run(self):
        current_block = self.provider.eth.getBlock('latest')

        while True:
            if current_block.number > last_confirmable_block(self.provider, config.blocks_confirmation_required):
                sleep(5)
            else:
                transactions = extract_tx_by_address(self.contract.address, current_block)
                for tx in transactions:
                    for callback in self.callbacks:
                        callback(tx)

                current_block += 1
