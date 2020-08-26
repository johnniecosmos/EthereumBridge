import subprocess
from threading import Thread, Event
from typing import List

from commands import create_multisign_account
from config import signing_accounts, threshold, multisig_account, manager_sleep_time_seconds
from db.collections.eth_swap import ETHSwap, Status
from db.collections.signatures import Signatures
from event_listener import EventListener
from util.web3 import unsigned_tx


class Manager:
    """Responsible of listening to new events Ethereum and generating corresponding records in DB """

    def __init__(self, event_listener: EventListener, multisig_threshold=2):
        event_listener.register(self._handle)
        self.multisig_threshold = multisig_threshold

        self.stop_signal = Event()
        Thread(target=self.run).start()

    def run(self):
        """Scans for signed transactions and updates status of multisig threshold achieved"""
        while not self.stop_signal.is_set():
            for transaction in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
                if Signatures.objects(tx_id=transaction.id).count() >= self.multisig_threshold:
                    transaction.status = Status.SWAP_STATUS_SIGNED.value
                    transaction.save()
            self.stop_signal.wait(manager_sleep_time_seconds)

    def _handle(self, event_logs: List[any]):
        """Registers transaction to the db"""
        for event in event_logs:
            if ETHSwap.objects(tx_hash=event.transactionHash.hex()).count() == 0:
                ETHSwap(tx_hash=event.transactionHash.hex(), status=Status.SWAP_STATUS_UNSIGNED.value,
                        unsigned_tx=unsigned_tx()).save()

    @classmethod
    def _init_multisig_account(cls):
        command = create_multisign_account.format(accounts=" ".join(signing_accounts), threshold=threshold,
                                                  account_name=multisig_account)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if err:
            raise RuntimeError(f"Couldn't create multisig account. {err}")
        return out
