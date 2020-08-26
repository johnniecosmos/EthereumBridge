from time import sleep

from mongoengine import DoesNotExist
import config

from db.collections.eth_swap import ETHSwap, Status
from db.collections.moderator import ModeratorData
from util.web3 import web3_provider, unsigned_tx


# noinspection PyUnresolvedReferences
class Moderator:
    """Iterates the block-chain and inserts contract tx to DB"""

    def __init__(self, contract_address="", provider_address=""):
        self.contract_address = contract_address if contract_address else config.contract_address
        self.provider_address = provider_address if provider_address else config.provider_address
        self.provider = web3_provider(self.provider_address)
        self.blocks_threshold = config.blocks_confirmation_required

        self.doc = self._resolve_last_block_scanned()
        self.run()

    # noinspection PyTypeChecker
    def run(self):      # TODO: IN CR, talk about the speed (55,170 per h)
        while True:
            block_number = self.doc.last_block + 1
            if not self.confirm_threshold(block_number, self.blocks_threshold):
                sleep(60)
                continue

            block = self.provider.eth.getBlock(block_number, full_transactions=True)
            transactions = self.extract_contract_tx(block)
            self.save(transactions)

            self.doc.last_block += 1
            self.doc.save()

    @staticmethod
    def _resolve_last_block_scanned():
        try:
            doc = ModeratorData.objects.get()
        except DoesNotExist:
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

    def confirm_threshold(self, block_num: int, threshold):
        """
        Validates that enough blocks (at least @thresh_hold) were generated after block number
        :param threshold: number of blocks that has to be generated after block_num
        :param block_num: the tested block
        :return: True if thresh holds else False
        """
        latest = self.provider.eth.getBlock('latest')
        if latest.number - block_num >= threshold:
            return True
        return False


if __name__ == "__main__":
    from db.setup import connect_default

    connect_default()
    Moderator()
