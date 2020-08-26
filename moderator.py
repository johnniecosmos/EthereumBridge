# This module will scan the block-chain and update DB if needed
from time import sleep

import config
from util.web3 import web3_provider, unsigned_tx
from db.collections.moderator import ModeratorData
from db.collections.eth_swap import ETHSwap, Status


class Moderator:
    def __init__(self, contract_address="", provider_address=""):
        self.contract_address = contract_address if contract_address else config.contract_address
        self.provider_address = provider_address if provider_address else config.provider_address
        self.provider = web3_provider(self.provider_address)

        self.doc = self.resolve_last_block_scanned()
        self.run()

    def run(self):
        while True:
            new_block = False
            try:
                block = self.provider.eth.getBlock(self.doc.last_block + 1, full_transactions=True)
                new_block = True
            except:
                continue

            transactions = self.extract_contract_tx(block)
            self.save(transactions)

            if not new_block:
                sleep(60)
            else:
                self.doc.last_block += 1  # might be heavy to the db
                self.doc.save()

    @staticmethod
    def resolve_last_block_scanned():
        try:
            doc = ModeratorData.objects.get()
        except:
            doc = ModeratorData(last_block=-1).save()

        return doc

    def extract_contract_tx(self, block) -> list:
        res = []
        for tx in block.transactions:
            if self.contract_address == tx.to:
                res.append(tx)

        return res

    @staticmethod
    def save(transactions):
        for tx in transactions:
            tx_hash = tx.hash.hex()
            if ETHSwap.objects(tx_hash=tx_hash).count() == 0:
                ETHSwap(tx_hash=tx_hash, status=Status.SWAP_STATUS_UNSIGNED.value, unsigned_tx=unsigned_tx()).save()


if __name__ == "__main__":
    from db.setup import *

    Moderator()
