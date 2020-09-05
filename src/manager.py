from threading import Thread, Event
from typing import List

from web3 import Web3

from src import config as temp_config
from src.contracts.contract import Contract
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from src.event_listener import EventListener
from src.signer import MultiSig
from src.util.exceptions import catch_and_log
from src.util.web3 import event_log, generate_unsigned_tx


class Manager:
    """Accepts new swap events and manages the tx status in db"""

    def __init__(self, event_listener: EventListener, contract: Contract, provider: Web3, multisig: MultiSig,
                 config=temp_config):
        self.contract = contract
        self.provider = provider
        self.config = config
        self.multisig = multisig

        self.stop_signal = Event()

        event_listener.register(self._handle)
        Thread(target=self.run).start()

    # noinspection PyUnresolvedReferences
    def run(self):
        """Scans for signed transactions and updates status if multisig threshold achieved"""
        while not self.stop_signal.is_set():
            for transaction in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
                if Signatures.objects(tx_id=transaction.id).count() >= self.config.signatures_threshold:
                    transaction.status = Status.SWAP_STATUS_SIGNED.value
                    transaction.save()
            self.stop_signal.wait(self.config.manager_sleep_time_seconds)

    def _handle(self, transactions: List[any]):
        """Registers transaction to the db"""

        self._handle_swap_events(transactions)

    def _handle_swap_events(self, events: List[any]):
        """Extracts tx of event 'swap' and saves to db"""
        for event in events:
            log = event_log(tx_hash=event.hash, event='Swap', provider=self.provider, contract=self.contract.contract)
            # noinspection PyUnresolvedReferences
            unsigned_tx, success = catch_and_log(generate_unsigned_tx, self.config.secret_contract_address, log,
                                                 self.config.chain_id, self.config.enclave_key,
                                                 self.config.enclave_hash, self.multisig.multisig_acc_addr,
                                                 "secret17fm5fn2ezhe8367ejge2wqvcg4lcawarpe2mzj")  # TODO: replace const
            if success:
                ETHSwap.save_web3_tx(log, unsigned_tx)
