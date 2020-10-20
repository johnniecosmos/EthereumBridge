from collections.abc import MutableMapping
from itertools import count
from threading import Event
from time import sleep
from typing import List, Callable, Iterator

from web3.exceptions import BlockNotFound

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.event_provider import EventProvider
from src.util.config import Config
from src.util.logger import get_logger
from src.util.web3 import contract_event_in_range, w3


class EthEventListener(EventProvider):
    """Tracks the block-chain for new transactions on a given address"""
    _ids = count(0)
    _chain = "ETH"

    def __init__(self, contract: EthereumContract, config: Config, **kwargs):
        # Note: each event listener can listen to one contract at a time
        self.id = next(self._ids)
        self.contract = contract
        self.config = config
        self.callbacks = Callbacks()
        self.logger = get_logger(db_name=config['db_name'],
                                 logger_name=config.get('logger_name', f"{self.__class__.__name__}-{self.id}"))
        self.events = []
        self.stop_event = Event()
        self.confirmations = config['eth_confirmations']
        super().__init__(group=None, name=f"EventListener-{config.get('logger_name', '')}", target=self.run, **kwargs)

    def register(self, callback: Callable, events: List[str]):
        """
        Allows registration to certain event of contract with confirmations threshold
        Note: events are Case Sensitive

        :param callback: callback function that will be invoked upon event
        :param events: list of events the caller wants to register to
        :param kwargs: ['confirmations'] number of confirmations to wait before triggering the event (default: 12)
        """

        for event_name in events:
            # event = getattr(self.contract.contract.events, event_name)
            self.logger.info(f"registering event {event_name}")
            self.events.append(event_name)
            self.callbacks[event_name] = callback

    def stop(self):
        self.logger.info("Stopping..")
        self.stop_event.set()

    def run(self):
        """Notify registered callbacks upon event occurrence"""
        self.logger.info("Starting..")

        block = w3.eth.blockNumber - self.confirmations
        while not self.stop_event.is_set():
            for event_name in self.events:
                self.logger.debug(f'Searching for event {event_name} in block #{block}..')
                try:
                    for evt in self.events_in_range(event_name, from_block=block, to_block=block):
                        self.logger.info(f"New event found {event_name}")
                        self.callbacks.trigger(event_name, evt)
                    block += 1
                except BlockNotFound:
                    self.logger.error(f'Block not found on block {block}')
                self.wait_for_block(block)

    def events_in_range(self, event: str, from_block: int, to_block: int = None):
        """ Returns a generator that yields all contract events in range"""
        return contract_event_in_range(self.contract, event, from_block=from_block,
                                       to_block=to_block)

    def wait_for_block(self, number: int) -> int:
        while True:
            block = (w3.eth.blockNumber - self.confirmations)
            if block >= number:
                return block
            sleep(self.config['sleep_interval'])


class Callbacks(MutableMapping):
    """Utility class that manages events registration by confirmation threshold"""

    def __iter__(self) -> Iterator:
        return iter(self.store)

    def __len__(self) -> int:
        return len(self.store)

    def __delitem__(self, key) -> None:
        del self.store[key]

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __setitem__(self, key, value):
        if key in self.store:
            self.store[key].extend(value)
        else:
            self.store[key] = [value]

    def __getitem__(self, key):
        if key not in self.store:
            return []
        return self.store[key]

    def trigger(self, event_name: str, event):
        """ call all the callbacks whose confirmation threshold reached """

        for callback in self[event_name]:
            callback(event)
