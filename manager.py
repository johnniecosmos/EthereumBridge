import subprocess
from threading import Thread
from typing import List

from commands import create_multisign_account
from config import signing_accounts, threshold, multisig_account
from db.eth_swap import ETHSwap, Status
from db.signatures import Signatures
from event_listener import EventListener


class Manager:
    """Responsible of listening to new events Ethereum and generating corresponding records in DB """

    def __init__(self, event_listener: EventListener, multisig_threshold=2):
        event_listener.register(self._handle)
        self.multisig_threshold = multisig_threshold
        self.multisig_account = multisig_account
        self.multisig_account_address = self._init_multisig_account()

        Thread(target=self.run).start()

    def run(self):
        """Scans for signed transactions and updates status"""
        while True:
            for transaction in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED):
                if Signatures.objects(tx=transaction.tx_id).count() > self.multisig_threshold:
                    transaction.status = Status.SWAP_STATUS_CONFIRMED
                    transaction.save()

    def _handle(self, event_logs: List[any]):
        """Registers transaction to the db"""
        for event in event_logs:
            if ETHSwap.objects(tx_hash=event.hash).count() == 0:  # TODO: might be too slow
                ETHSwap(tx_hash=event.hash, signer=self.multisig_account, status=Status.SWAP_STATUS_UNSIGNED,
                        unsigned_tx=self._unsigned_tx()).save()

    @classmethod
    def _init_multisig_account(cls):
        command = create_multisign_account.format(accounts=" ".join(signing_accounts), threshold=threshold,
                                                  account_name=multisig_account)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if err:
            raise RuntimeError(f"Couldn't create multisig account. {err}")
        return out

    @staticmethod
    def _unsigned_tx(contract: str = "0xabcdefg...", recipient: str = "0xABCDEFG...", amount: int = 1):
        return {"contract": contract, "recipient": recipient, "amount": amount}
