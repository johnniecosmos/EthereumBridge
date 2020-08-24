from typing import List

import subprocess
from commands import create_multisign_account
from config import signing_accounts, threshold, multisig_account
from db.eth_swap import ETHSwap, Status
from db.signatures import Signatures
from event_listener import EventListener


class Leader:
    def __init__(self, event_listener: EventListener, multisig_threshold=2):
        event_listener.register(self._handle)
        self.multisig_threshold = multisig_threshold
        self.multisig_account = multisig_account
        self.multisig_account_address = self._init_multisig_account()

        self.run()

    def run(self):
        """Scans for signed transactions, verifies and mints token in scrt"""
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
                        unsigned_tx=self._generate_tx()).save()

    @classmethod
    def _init_multisig_account(cls):
        command = create_multisign_account.format(accounts=" ".join(signing_accounts), threshold=threshold,
                                                  account_name=multisig_account)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if err:
            raise RuntimeError(f"Couldn't create multisig account. {err}")
        return out

    def _generate_tx(self):
        raise NotImplementedError
