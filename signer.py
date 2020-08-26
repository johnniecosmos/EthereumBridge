from threading import Lock

from mongoengine import signals

from db.collections.eth_swap import ETHSwap, Status
from db.collections.signatures import Signatures


class Signer:
    def __init__(self, enc_key=""):  # TODO: Figure out the keys that signers are required to have
        self.enc_key = enc_key
        self.lock = Lock()
        signals.post_save.connect(self.new_tx_signal, sender=ETHSwap)

        self.catch_up()

    def catch_up(self):
        for tx in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
            self.sign_tx(tx)

    def sign_tx(self, tx: ETHSwap):
        signed_tx = self.enc_key  # TODO: use secretcli to sign
        if not Signatures.objects(tx_id=tx.id, signed_tx=signed_tx).count() == 0:
            return  # avoid duplicate records in db

        with self.lock:  # used by two threads, the main thread and the signals thread
            Signatures(tx_id=tx.id, signed_tx=signed_tx).save()

    # noinspection PyUnusedLocal
    def new_tx_signal(self, sender, document, **kwargs):
        if not document.status == Status.SWAP_STATUS_UNSIGNED.value:
            return  # TODO: might be able to improve notification filter
        self.sign_tx(document)
