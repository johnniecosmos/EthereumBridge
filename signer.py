import json
from collections import namedtuple
from os import remove
from tempfile import NamedTemporaryFile
from threading import Lock

from hexbytes import HexBytes
from mongoengine import signals
from web3 import Web3

from contracts.contract import Contract
from db.collections.eth_swap import ETHSwap, Status
from db.collections.log import Logs
from db.collections.signatures import Signatures
from util.exceptions import catch_and_log
from util.secretcli import sign_tx as secretcli_sign
from util.web3 import event_logs

multisig = namedtuple('Multisig', ['multisig_acc_addr', 'signer_acc_name'])


class Signer:
    def __init__(self, provider: Web3, multisig_: multisig, contract: Contract):
        self.provider = provider
        self.multisig = multisig_
        self.contract = contract
        self.lock = Lock()
        signals.post_save.connect(self.new_tx_signal, sender=ETHSwap)

        self.catch_up()

    def catch_up(self):
        for tx in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
            self._sign_tx(tx)

    # noinspection PyUnusedLocal
    def new_tx_signal(self, sender, document, **kwargs):
        if not document.status == Status.SWAP_STATUS_UNSIGNED.value:
            return  # TODO: might be able to improve notification filter
        self._sign_tx(document)

    def _sign_tx(self, tx: ETHSwap):
        if self.is_signed(tx):
            return

        if not self.is_valid(tx):
            return

        # noinspection PyBroadException
        signed_tx_file, success = catch_and_log(self._sign_with_secret_cli, tx.unsigned_tx)

        with self.lock:  # used by both the "catchup()" and the notifications from DB
            if success:
                with signed_tx_file as f:
                    Signatures(tx_id=tx.id, signed_tx=json.load(f)).save()

    def is_signed(self, tx: ETHSwap) -> bool:
        """ Returns True if tx was already signed, else False """
        if Signatures.objects(tx_id=tx.id, signer=self.multisig.signer_acc_name).count() > 0:
            return True
        return False

    def is_valid(self, tx: ETHSwap) -> bool:
        """Assert that the data in the unsigned_tx matches the tx on the chain"""
        log = event_logs(tx.tx_hash, 'Swap', self.provider, self.contract.contract)
        unsigned_tx = json.loads(tx.unsigned_tx)
        try:
            assert unsigned_tx['contract_addr'].lower() == log.address.lower()
            assert unsigned_tx['recipient'] == HexBytes(log.args.to).hex()
            assert unsigned_tx['amount'] == log.args.amount
        except AssertionError as e:
            Logs(log=repr(e)).save()

        return True

    def _sign_with_secret_cli(self, unsigned_tx: str):

        with NamedTemporaryFile(mode="w+", delete=False) as f:
            unsigned_path = f.name
            f.write(unsigned_tx)

        fd = NamedTemporaryFile(mode="w+")

        secretcli_sign(unsigned_path, self.multisig.multisig_acc_addr, self.multisig.signer_acc_name, fd.name)
        remove(unsigned_path)

        return fd
