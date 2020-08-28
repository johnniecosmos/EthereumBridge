from time import sleep

from hexbytes import HexBytes
from mongoengine import DoesNotExist, MultipleObjectsReturned
from web3 import Web3

import config
from contracts.contract import Contract
from db.collections.eth_swap import ETHSwap
from db.collections.log import Logs
from db.collections.moderator import ModeratorData
from util.exceptions import catch_and_log
from util.web3 import last_confirmable_block, extract_tx_by_address, event_logs, normalize_address


class Moderator:
    """Iterates the block-chain and inserts contract tx to DB"""

    def __init__(self, contract_: Contract, provider_: Web3):
        self.provider = provider_
        self.contract = contract_

        self.blocks_threshold = config.blocks_confirmation_required

        self.doc = self._resolve_last_block_scanned()
        self.run()

    # noinspection PyTypeChecker
    def run(self):
        while True:
            block_number = self.doc.last_block + 1
            if not self.confirm_threshold(block_number, self.blocks_threshold):
                sleep(60)
                continue

            block = self.provider.eth.getBlock(block_number, full_transactions=True)
            transactions = self.extract_contract_tx(block)
            swap_transactions = self.extract_swap_tx(transactions)
            for tx in swap_transactions:
                # noinspection PyBroadException
                recipient = HexBytes(tx.args.to).hex()
                unsigned_tx, success = catch_and_log(self.contract.generate_unsigned_tx,
                                                     normalize_address(tx.address),
                                                     recipient,
                                                     tx.args.amount)
                if success:  # Note: Any tx that is failed here will be be skipped for eternity
                    ETHSwap.save_web3_tx(tx, unsigned_tx)

            self.doc.last_block += 1
            self.doc.save()

    @staticmethod
    def _resolve_last_block_scanned():
        try:
            doc = ModeratorData.objects.get()
        except DoesNotExist:
            doc = ModeratorData(last_block=-1).save()
        except MultipleObjectsReturned as e:  # Corrupted DB
            Logs(log=repr(e)).save()
            raise e

        return doc

    def extract_contract_tx(self, block) -> list:
        return extract_tx_by_address(self.contract.address, block)

    def confirm_threshold(self, block_num: int, threshold):
        """
        Validates that enough blocks (at least @thresh_hold) were generated after @block_number
        :param threshold: number of blocks that has to be generated after @block_num
        :param block_num: the tested block
        :return: True if threshold stands else False
        """
        if last_confirmable_block(self.provider, threshold) - block_num >= 0:
            return True

        return False

    def extract_swap_tx(self, transactions) -> list:
        if not transactions:
            return []

        res = []
        data_index = 0
        for tx in transactions:
            log = event_logs(tx.hash, 'Swap', self.provider, self.contract.contract)
            if log:
                res.append(log[data_index])

        return res


if __name__ == "__main__":
    from db.setup import connect_default
    from util.web3 import web3_provider

    provider = web3_provider("wss://ropsten.infura.io/ws/v3/e5314917699a499c8f3171828fac0b74")
    contract = Contract(provider, "0xfc4589c481538f29ad738a13da49af79d93ecb21")

    connect_default()
    Moderator(contract, provider)
