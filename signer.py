# Scan for tx with status SWAP_STATUS_UNSIGNED
# Add transaction to Signatures collection
from time import sleep

from db.collections.eth_swap import ETHSwap, Status
from db.collections.signatures import Signatures
from mongoengine import signals
from threading import Thread, Lock


class Signer:
    def __init__(self, some_key=""):  # TODO: Figure out the keys that signers are required to have
        self.some_key = some_key
        self.processed_transactions = set()
        self.lock = Lock()
        signals.post_save.connect(self.new_tx_signal, sender=ETHSwap)

        Thread(target=self.catch_up).start()  # if notifications work, not needed

    def catch_up(self):
        while True:
            for tx in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
                if tx.tx_hash not in self.processed_transactions:
                    try:
                        self.sign_tx(tx)
                    except:
                        pass # TODO, log it - shouldn't happen, ever, sanity check.

            sleep(5)

    def sign_tx(self, tx: ETHSwap):
        if not Signatures.objects(tx_id=tx.id, signed_tx=self.some_key).count() == 0:
            return  # avoid duplicate records in db

        with self.lock:
            Signatures(tx_id=tx.id, signed_tx=self.some_key).save()
            self.processed_transactions.add(tx.tx_hash)

    def new_tx_signal(self, sender, document, **kwargs):
        self.sign_tx(document)
