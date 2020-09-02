from time import sleep

from mongoengine import DoesNotExist, MultipleObjectsReturned
from web3 import Web3

from src import config as temp_config
from src.contracts.contract import Contract
from src.db.collections.eth_swap import ETHSwap
from src.db.collections.log import Logs
from src.db.collections.moderator import ModeratorData
from src.util.exceptions import catch_and_log
from src.util.web3 import last_confirmable_block, extract_tx_by_address, event_log, generate_unsigned_tx


class Moderator:
    """Iterates the block-chain and inserts 'missed' swap tx to DB"""

    def __init__(self, contract_: Contract, provider_: Web3, config=temp_config):
        self.provider = provider_
        self.contract = contract_

        self.config = config

        self.doc = self._resolve_last_block_scanned()
        self.run()

    # noinspection PyTypeChecker
    def run(self):
        while True:
            block_number = self.doc.last_block + 1
            if not self.confirm_threshold(block_number, self.config.blocks_confirmation_required):
                sleep(60)
                continue

            block = self.provider.eth.getBlock(block_number, full_transactions=True)
            transactions = self.extract_contract_tx(block)
            swap_transactions = self.extract_swap_tx(transactions)
            for log in swap_transactions:
                # noinspection PyBroadException
                unsigned_tx, success = catch_and_log(generate_unsigned_tx, self.config.secret_contract_address,
                                                     log, self.config.chain_id, self.config.enclave_key,
                                                     self.config.enclave_hash, self.multisig.multisig_acc_addre,
                                                     "secret17fm5fn2ezhe8367ejge2wqvcg4lcawarpe2mzj")  # TODO: replace const
                if success:  # Note: Any tx that is failed here will be be skipped for eternity
                    ETHSwap.save_web3_tx(log, unsigned_tx)

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
            log = event_log(tx.hash, 'Swap', self.provider, self.contract.contract)
            if log:
                res.append(log[data_index])

        return res
