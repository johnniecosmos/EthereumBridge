from json import loads
from threading import Thread
from time import sleep

from web3 import Web3
from util.web3 import web3_provider

import config
from temp import abi


class EventListener:
    def __init__(self, contract_address="", provider_address=""):
        self.contract_address = contract_address if contract_address else config.contract_address
        self.provider_address = provider_address if provider_address else config.provider_address
        self.abi = loads(abi)  # TODO: Receive from ctor
        self.callbacks = []
        Thread(target=self.run).start()

    def register(self, callback: callable):
        self.callbacks.append(callback)

    # TODO: check if provider can recover from node downtime
    def run(self):
        provider = web3_provider(self.provider_address)
        address_ = self.contract_address
        try:  # TODO: Verify desired behaviour
            address_ = Web3.toChecksumAddress(address_)
        except:
            pass

        contract = provider.eth.contract(address=address_, abi=abi)
        filter = contract.events.Swap.createFilter(fromBlock='latest', address=address_)

        # Main execution loop, waits new events on confirmed blocks
        while True:
            new_entries = filter.get_new_entries()
            if new_entries:
                for callback in self.callbacks:
                    callback(new_entries)
                continue
            sleep(5)
