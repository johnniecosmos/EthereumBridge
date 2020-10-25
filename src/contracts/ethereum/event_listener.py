from collections.abc import MutableMapping
from itertools import count
from threading import Event
from time import sleep
from typing import List, Callable, Iterator, Generator, Dict, Tuple, Union

from asyncio import Queue

from web3.exceptions import BlockNotFound
from web3.contract import LogFilter, LogReceipt

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.event_provider import EventProvider
from src.util.config import Config
from src.util.logger import get_logger
from src.util.web3 import contract_event_in_range, w3, extract_tx_by_address, event_log


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
        self.pending_events: List[Tuple[str, LogReceipt]] = []
        self.filters: Dict[str, LogFilter] = {}
        self.stop_event = Event()
        self.queue = Queue()
        self.confirmations = config['eth_confirmations']
        super().__init__(group=None, name=f"EventListener-{config.get('logger_name', '')}", target=self.run, **kwargs)
        self.setDaemon(True)

    def register(self, callback: Callable, events: List[str], from_block = "latest"):
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

            event = getattr(self.contract.contract.events, event_name)
            evt_filter = event.createFilter(fromBlock="latest")
            self.filters[event_name] = evt_filter

            if from_block != "latest":
                self.add_events_in_range(event_name, from_block=from_block, to_block=w3.eth.blockNumber)

    def stop(self):
        self.logger.info("Stopping..")
        self.stop_event.set()

    def run(self):
        """Notify registered callbacks upon event occurrence"""
        self.logger.info("Starting..")

        # block = w3.eth.blockNumber - self.confirmations
        while not self.stop_event.is_set():
            self.logger.debug('Scanning for new events')
            for name, event in self.get_new_events():
                self.logger.info(f"New event found {name}, adding to confirmation handler")
                # self.callbacks.trigger(name, event)
                self.pending_events.append((name, event))
            for name, event in self.confirmation_handler():
                self.logger.info(f"Event {name} passed confirmation limit, executing callback")
                self.callbacks.trigger(name, event)
            # except BlockNotFound:
            #     self.logger.error(f'Block not found {block}')
            #     # block = self.wait_for_block(block)

            sleep(self.config['sleep_interval'])

    def confirmation_handler(self):
        blockNum = w3.eth.blockNumber
        # this creates a copy of the list, so we can remove from the original one while still iterating
        for item in list(self.pending_events):
            if item[1].blockNumber <= (blockNum - self.confirmations):
                self.pending_events.remove(item)
                yield item[0], item[1]

    def events_in_range(self, event: str, from_block: int, to_block: int = None):
        """ Returns a generator that yields all contract events in range"""
        return contract_event_in_range(self.contract, event, from_block=from_block,
                                       to_block=to_block)

    def add_events_in_range(self, event_name, from_block: Union[int, str], to_block: int):
        """
        Used to catch up for all the events from when we wanted to start, and where we are now.
        Todo: check on ropsten and mainnet if this behaves the same way
        """
        event = getattr(self.contract.contract.events, event_name)
        evt_filter = event.createFilter(fromBlock=from_block, toBlock=to_block)
        for event in evt_filter.get_all_entries():
            self.pending_events.append((event_name, event))

    def wait_for_block(self, number: int) -> int:
        while True:
            block = (w3.eth.blockNumber - self.confirmations)
            if block >= number:
                return block
            sleep(self.config['sleep_interval'])

    def confirmation_manager(self):
        pass

    def get_new_events(self):
            """
            scans the blockchain, and yields blocks that has contract tx with the provided event

            Note: Be cautions with the range provided, as the logic creates query for each block which could be a bottleneck.
            :param from_block: starting block, defaults to 0
            :param to_block: end block, defaults to 'latest'
            :param provider:
            :param logger:
            :param contract:
            :param event_name: name of the contract emit event you wish to be notified of
            """
            for name, log_filter in self.filters.items():
                for event in log_filter.get_new_entries():
                    yield name, event
            # block = w3.eth.getBlock(block_num, full_transactions=True)
            # contract_transactions = extract_tx_by_address(self.contract, block)
            # self.logger.debug(f'Searching for events in block #{block}..')
            # if not contract_transactions:
            #     return
            # for tx in contract_transactions:
            #
            #     event, log = event_log(tx_hash=tx.hash, events=self.events, provider=w3, contract=self.contract.contract)
            #     if log is None:
            #         continue
            #     yield event, log

            # for filter in filters:
            #     for tx in filter.get_new_entries():
            #         await self.queue.put(tx)

            # for block_num in range(from_block, to_block + 1):
            #     block = provider.eth.getBlock(block_num, full_transactions=True)
            #     contract_transactions = extract_tx_by_address(contract.address, block)
            #
            #     if not contract_transactions:
            #         continue

            # raise StopIteration()

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
