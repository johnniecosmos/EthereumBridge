from threading import Thread, Event

from web3.datastructures import AttributeDict

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.secret.secret_contract import mint_json
from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.management import Management, Source
from src.db.collections.signatures import Signatures
from src.event_listener import EventListener
from src.signer.secret_signer import SecretAccount
from src.util.config import Config
from src.util.logger import get_logger
from src.util.secretcli import create_unsigned_tx


class Manager:
    """Registers to contract event and manages tx state in DB"""

    def __init__(self, event_listener: EventListener, contract: EthereumContract,
                 multisig: SecretAccount, config: Config):
        self.contract = contract
        self.config = config
        self.multisig = multisig
        self.event_listener = event_listener

        self.logger = get_logger("Manager", db_name=self.config.get('db_name', ''))
        self.stop_signal = Event()

        event_listener.register(self._handle, [contract.tracked_event()], self.config['eth_confirmations'])
        self.catch_up()
        Thread(target=self.run).start()

    # noinspection PyUnresolvedReferences
    def run(self):
        """Scans for signed transactions and updates status if multisig threshold achieved"""
        while not self.stop_signal.is_set():
            for transaction in ETHSwap.objects(status=Status.SWAP_STATUS_UNSIGNED.value):
                if Signatures.objects(tx_id=transaction.id).count() >= self.config['signatures_threshold']:
                    transaction.status = Status.SWAP_STATUS_SIGNED.value
                    transaction.save()
            self.stop_signal.wait(self.config['sleep_interval'])

    def catch_up(self):
        from_block = Management.last_processed(Source.eth.value) + 1
        self.logger.debug(f'Starting to catch up from block {from_block}')
        if self.config['eth_start_block'] > from_block:
            self.logger.debug(f'Due to config fast forwarding to block {self.config["eth_start_block"]}')
            from_block = self.config['eth_start_block']
            Management.update_last_processed(Source.eth.value, from_block)

        to_block = \
            self.event_listener.provider.eth.getBlock('latest').number - self.config['eth_confirmations']

        if to_block <= 0:
            return

        self.logger.debug(f'Catching up to current block: {to_block}')

        for event in self.event_listener.events_in_range(self.contract.tracked_event(), from_block, to_block):
            self.logger.info(f'Found new event at block: {event["blockNumber"]}')
            self._handle(event)

    def _handle(self, event: AttributeDict):
        """Extracts tx data from @event and add unsigned_tx to db"""
        if not self.contract.verify_destination(event):
            return

        amount, _ = self.contract.extract_amount(event), self.contract.extract_addr(event)

        try:
            block_number, tx_hash, recipient = self._validate_event(event)
        except ValueError:
            return

        mint = mint_json(amount, tx_hash, recipient)
        try:
            unsigned_tx = create_unsigned_tx(self.config['secret_contract_address'], mint, self.config['chain_id'],
                                             self.config['enclave_key'], self.config['code_hash'],
                                             self.multisig.address)

            # if ETHSwap.objects(tx_hash=tx_hash).count() == 0:  # TODO: exception because of force_insert?
            tx = ETHSwap(tx_hash=tx_hash, status=Status.SWAP_STATUS_UNSIGNED.value, unsigned_tx=unsigned_tx)
            tx.save(force_insert=True)

            Management.update_last_processed(src=Source.eth.value, update_val=block_number)
        except (IndexError, AttributeError) as e:
            self.logger.error(msg=f"Failed on tx {tx_hash}, block {block_number}, "
                                  f"due to missing config: {e}")
        except RuntimeError as e:
            self.logger.error(msg=f"Failed to create swap tx for eth hash {tx_hash}, block {block_number}. Error: {e}")

    def _validate_event(self, event: AttributeDict):
        try:
            block_number = event["blockNumber"]
        except IndexError:
            self.logger.error(msg=f"Failed to decode block number for event {event}")
            raise ValueError from None

        try:
            tx_hash = event["transactionHash"].hex()
        except (IndexError, AttributeError) as e:
            self.logger.error(msg=f"Failed to decode transaction hash for block {block_number}: {e}")
            raise ValueError from None

        try:
            recipient = event.args.recipient.decode()
        except (ValueError, AttributeError):
            self.logger.error(msg=f"Failed to decode recipient for block {block_number}, transaction: {tx_hash}")
            raise ValueError from None

        return block_number, tx_hash, recipient
