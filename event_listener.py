from threading import Thread
from time import sleep

from web3 import Web3

import config
from contracts.contract import Contract
from util.web3 import last_confirmable_block, extract_tx_by_address


class EventListener:
    """Tracks the block-chain for new transactions on a given address"""

    def __init__(self, contract: Contract, provider: Web3):
        self.provider = provider
        self.contract = contract

        self.callbacks = []

        Thread(target=self.run).start()

    def register(self, callback: callable):
        self.callbacks.append(callback)

    def run(self):
        current_block = self.provider.eth.getBlock('latest')

        while True:
            if current_block.number > last_confirmable_block(self.provider, config.blocks_confirmation_required):
                sleep(5)  # TODO: Code Review: so, I used to have a push notification over here - however you can't
                          #  filter with confirmation threshold, so i changed it to pooling. I can create my own
                          #  notification mechanisem, but it will add complexity to somethign that should be simple.
                          #  let me know what you thinking.
            else:
                transactions = extract_tx_by_address(self.contract.address, current_block)
                for tx in transactions:
                    for callback in self.callbacks:
                        callback(tx)

                current_block += 1
