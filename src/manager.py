from threading import Thread, Event

from web3.datastructures import AttributeDict

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.secret.secret_contract import mint_json
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.management import Management, Source
from src.db.collections.signatures import Signatures
from src.event_listener import EventListener
from src.singer.secret_signer import MultiSig
from src.util.logger import get_logger
from src.util.secretcli import create_unsigned_tx


class Manager:
    """Registers to contract event and manages tx state in DB"""

    def __init__(self, event_listener: EventListener, contract: EthereumContract, multisig: MultiSig, config):
        self.contract = contract
        self.config = config
        self.multisig = multisig
        self.event_listener = event_listener

        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)
        self.stop_signal = Event()

        event_listener.register(self._handle, [contract.tracked_event()], self.config.blocks_confirmation_required)
        self.catch_up()
        Thread(target=self.run).start()

    # noinspection PyUnresolvedReferences
    def run(self):
        """Scans for signed transactions and updates status if multisig threshold achieved"""
        while not self.stop_signal.is_set():
            for transaction in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
                if Signatures.objects(tx_id=transaction.id).count() >= self.config.signatures_threshold:
                    transaction.status = Status.SWAP_STATUS_SIGNED.value
                    transaction.save()
            self.stop_signal.wait(self.config.manager_sleep_time_seconds)

    def catch_up(self):
        from_block = Management.last_processed(Source.eth.value, self.logger) + 1
        if self.config.ethr_start_block > from_block:
            from_block = self.config.ethr_start_block
            Management.update_last_processed(Source.eth.value, from_block)

        to_block = self.event_listener.provider.eth.getBlock('latest').number - self.config.blocks_confirmation_required

        if to_block <= 0:
            return

        for event in self.event_listener.events_in_range(self.contract.tracked_event(), from_block, to_block):
            self._handle(event)

    def _handle(self, event: AttributeDict):
        """Extracts tx data from @event and add unsigned_tx to db"""
        if not self.contract.verify_destination(event):
            return

        amount, dest = self.contract.extract_amount(event), self.contract.extract_addr(event)
        mint = mint_json(amount, event.transactionHash.hex(), event.args.recipient.decode())
        try:
            unsigned_tx = create_unsigned_tx(self.config.secret_contract_address, mint, self.config.chain_id,
                                             self.config.enclave_key, self.config.code_hash,
                                             self.multisig.multisig_acc_addr)

            tx_hash = event.transactionHash.hex()
            # if ETHSwap.objects(tx_hash=tx_hash).count() == 0:  # TODO: exception becaose of force_insert?
            tx = ETHSwap(tx_hash=tx_hash, status=Status.SWAP_STATUS_UNSIGNED.value, unsigned_tx=unsigned_tx)
            tx.save(force_insert=True)

            Management.update_last_processed(src=Source.eth.value, update_val=event.blockNumber)
        except Exception as e:
            self.logger.error(msg=f"Failed on tx {event.transactionHash.hex()}, block {event.blockNumber}. Error: {e}")
