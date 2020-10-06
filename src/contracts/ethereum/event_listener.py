from itertools import count
from threading import Thread, Event, Lock
from time import sleep
from typing import List, Callable, Dict

from web3 import Web3
from web3.exceptions import BlockNotFound

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.event_provider import EventProvider
from src.util.config import Config
from src.util.logger import get_logger
from src.util.web3 import extract_tx_by_address, event_log, contract_event_in_range, web3_provider


class EthEventListener(EventProvider):
    """Tracks the block-chain for new transactions on a given address"""
    _ids = count(0)
    _chain = "ETH"

    def __init__(self, contract: EthereumContract, config: Config, **kwargs):
        # Note: each event listener can listen to one contract at a time
        self.id = next(self._ids)
        self.provider = web3_provider(config['eth_node_address'])
        self.contract = contract
        self.config = config
        self.callbacks = Callbacks()
        self.logger = get_logger(db_name=config['db_name'],
                                 logger_name=config.get('logger_name', f"{self.__class__.__name__}-{self.id}"))

        self.stop_event = Event()
        super().__init__(group=None, name=f"EventListener-{config.get('logger_name', '')}", target=self.run, **kwargs)

    def register(self, callback: Callable, events: List[str], *args, **kwargs):
        """
        Allows registration to certain event of contract with confirmations threshold
        Note: events are Case Sensitive

        :param callback: callback function that will be invoked upon event
        :param events: list of events the caller wants to register to
        :param kwargs: ['confirmations'] number of confirmations to wait before triggering the event (default: 12)
        """
        confirmations_required = kwargs.get('confirmations', 12)
        for event in events:
            self.callbacks.add(event, callback, confirmations_required)

    def stop(self):
        self.logger.info("Stopping..")
        self.stop_event.set()

    def run(self):
        """Notify registered callbacks upon event occurrence"""
        self.logger.info("Starting..")
        current_block_num = self.provider.eth.getBlock('latest').number

        while not self.stop_event.is_set():
            try:
                block = self.provider.eth.getBlock(current_block_num, full_transactions=True)
                self.callbacks.call(self.provider, self.contract, block.number)
            except BlockNotFound:
                sleep(self.config['sleep_interval'])
                continue

            current_block_num += 1

    def events_in_range(self, event: str, from_block: int, to_block: int = None):
        """ Returns a generator that yields all contract events in range"""
        return contract_event_in_range(self.provider, self.contract, event, from_block=from_block,
                                       to_block=to_block)


class Callbacks:
    """Utility class that manages events registration by confirmation threshold"""

    def __init__(self):
        self.callbacks_by_confirmations: Dict[int, Dict[str, List[Callable]]] = dict()
        self.lock = Lock()

    def add(self, event_name: str, callback: Callable, confirmations_required: int):
        with self.lock:
            callbacks = self.callbacks_by_confirmations.setdefault(confirmations_required, dict())
            callbacks = callbacks.setdefault(event_name, list())
            callbacks.append(callback)

    def call(self, provider: Web3, contract: EthereumContract, block_number: int):
        """ call all the callbacks whose confirmation threshold reached """

        for threshold, callbacks in self.callbacks_by_confirmations.items():
            if block_number - threshold <= 0:
                continue

            block = provider.eth.getBlock(block_number - threshold, full_transactions=True)
            contract_transactions = extract_tx_by_address(contract.address, block)

            if not contract_transactions:
                continue

            for tx in contract_transactions:
                event_name, log = event_log(tx_hash=tx.hash, events=list(callbacks.keys()), provider=provider,
                                            contract=contract.contract)
                if log is None:
                    continue

                for callback in callbacks[event_name]:
                    callback(log)
