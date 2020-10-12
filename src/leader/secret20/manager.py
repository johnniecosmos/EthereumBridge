from threading import Thread, Event

from web3.datastructures import AttributeDict

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.secret.secret_contract import mint_json
from src.db.collections.eth_swap import Swap, Status
from src.db.collections.management import Management, Source
from src.db.collections.signatures import Signatures
from src.contracts.ethereum.event_listener import EthEventListener
from src.signer.secret20.signer import SecretAccount
from src.util.common import Token
from src.util.config import Config
from src.util.logger import get_logger
from src.util.secretcli import create_unsigned_tx
from src.util.web3 import get_block


class SecretManager(Thread):
    """Registers to contract event and manages tx state in DB"""

    def __init__(self, contract: EthereumContract,
                 s20_contract: Token,
                 multisig: SecretAccount, config: Config, **kwargs):
        self.contract = contract
        self.s20_address = s20_contract.address
        self.config = config
        self.multisig = multisig
        self.event_listener = EthEventListener(contract, config)

        self.logger = get_logger(db_name=self.config['db_name'],
                                 logger_name=config.get('logger_name',
                                                        f"{self.__class__.__name__}-{self.multisig.name}"))
        self.stop_signal = Event()

        self.event_listener.register(self._handle, [contract.tracked_event()],)
        super().__init__(group=None, name="SecretManager", target=self.run, **kwargs)

    def stop(self):
        self.logger.info("Stopping..")
        self.event_listener.stop()
        self.stop_signal.set()

    def run(self):
        """Scans for signed transactions and updates status if multisig threshold achieved"""
        self.logger.info("Starting..")
        self.catch_up()

        self.event_listener.start()
        self.logger.info("Done catching up")

        while not self.stop_signal.is_set():
            for transaction in Swap.objects(status=Status.SWAP_UNSIGNED):
                self.logger.debug(f"Checking unsigned tx {transaction.id}")
                if Signatures.objects(tx_id=transaction.id).count() >= self.config['signatures_threshold']:
                    self.logger.info(f"Found tx {transaction.id} with enough signatures to broadcast")
                    transaction.status = Status.SWAP_SIGNED
                    transaction.save()
                    self.logger.info(f"Set status of tx {transaction.id} to signed")
                else:
                    self.logger.debug(f"Tx {transaction.id} does not have enough signatures")
            self.stop_signal.wait(self.config['sleep_interval'])

    def catch_up(self):
        from_block = Management.last_processed(Source.ETH.value) + 1
        self.logger.debug(f'Starting to catch up from block {from_block}')
        if self.config['eth_start_block'] > from_block:
            self.logger.debug(f'Due to config fast forwarding to block {self.config["eth_start_block"]}')
            from_block = self.config['eth_start_block']
            Management.update_last_processed(Source.ETH.value, from_block)

        to_block = get_block('latest').number - self.config['eth_confirmations']

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

        amount = self.contract.extract_amount(event)

        try:
            block_number, tx_hash, recipient = self._parse_event(event)
        except ValueError:
            return

        mint = mint_json(amount, tx_hash, recipient)
        try:
            unsigned_tx = create_unsigned_tx(self.s20_address, mint, self.config['chain_id'],
                                             self.config['enclave_key'], self.config['code_hash'],
                                             self.multisig.address)

            # if ETHSwap.objects(tx_hash=tx_hash).count() == 0:  # TODO: exception because of force_insert?
            tx = Swap(src_tx_hash=tx_hash, status=Status.SWAP_UNSIGNED, unsigned_tx=unsigned_tx)
            tx.save(force_insert=True)
            self.logger.info(f"saved new eth -> scrt transaction {tx_hash}")
            Management.update_last_processed(src=Source.ETH.value, update_val=block_number)
        except (IndexError, AttributeError) as e:
            self.logger.error(f"Failed on tx {tx_hash}, block {block_number}, "
                              f"due to missing config: {e}")
        except RuntimeError as e:
            self.logger.error(f"Failed to create swap tx for eth hash {tx_hash}, block {block_number}. Error: {e}")

    def _parse_event(self, event: AttributeDict):
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
