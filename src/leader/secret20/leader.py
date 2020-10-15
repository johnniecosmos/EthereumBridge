import json
from datetime import datetime
from threading import Thread, Event
from time import sleep
from typing import List

from mongoengine import OperationError

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.db.collections.eth_swap import Swap, Status
from src.db.collections.signatures import Signatures
from src.leader.secret20.manager import SecretManager
from src.signer.secret20.signer import SecretAccount
from src.util.common import temp_file, temp_files, Token
from src.util.config import Config
from src.util.logger import get_logger
from src.util.secretcli import broadcast, multisig_tx, query_data_success

BROADCAST_VALIDATION_COOLDOWN = 60
SCRT_BLOCK_TIME = 7


class Secret20Leader(Thread):
    """ Broadcasts signed Secret-20 minting tx after successful ETH or ERC20 swap event """

    def __init__(self,
                 secret_multisig: SecretAccount,
                 s20_contract: Token,
                 contract: EthereumContract,
                 config: Config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.multisig_name = secret_multisig.name
        self.config = config
        self.manager = SecretManager(contract, s20_contract, secret_multisig, config)
        self.logger = get_logger(db_name=self.config['db_name'],
                                 logger_name=config.get('logger_name', f"{self.__class__.__name__}-{self.multisig_name}"))
        self.stop_event = Event()

        super().__init__(group=None, name="SecretLeader", target=self.run, **kwargs)

    def _catch_up(self):
        """ Scans the DB for signed swap tx at startup """
        # Note: As Collection.objects() call is cached, there shouldn't be collisions with DB signals
        for tx in Swap.objects(status=Status.SWAP_SIGNED):
            self._create_and_broadcast(tx)

    def stop(self):
        self.logger.info("Stopping")
        self.manager.stop()
        self.stop_event.set()

    def run(self):
        self.logger.info("Starting")
        self.manager.start()
        self._scan_swap()

    def _scan_swap(self):
        while not self.stop_event.is_set():
            for tx in Swap.objects(status=Status.SWAP_SIGNED):
                self.logger.info(f"Found tx ready for broadcasting {tx.id}")
                self._create_and_broadcast(tx)
                sleep(SCRT_BLOCK_TIME)
            for tx in Swap.objects(status=Status.SWAP_SUBMITTED):
                self._broadcast_validation(tx)
            self.logger.debug('done scanning for swaps. sleeping..')
            self.stop_event.wait(self.config['sleep_interval'])

    def _create_and_broadcast(self, tx: Swap):
        # reacts to signed tx in the DB that are ready to be sent to secret20
        signatures = [signature.signed_tx for signature in Signatures.objects(tx_id=tx.id)]
        if len(signatures) < self.config['signatures_threshold']:  # sanity check
            self.logger.error(msg=f"Tried to sign tx {tx.id}, without enough signatures"
                                  f" (required: {self.config['signatures_threshold']}, have: {len(signatures)})")
            return

        try:
            signed_tx = self._create_multisig(tx.unsigned_tx, signatures)
            scrt_tx_hash = self._broadcast(signed_tx)
            self.logger.info(f"Broadcasted {tx.id} successfully - {scrt_tx_hash}")
            tx.status = Status.SWAP_SUBMITTED
            tx.dst_tx_hash = scrt_tx_hash
            tx.save()
            self.logger.info(f"Changed status of tx {tx.id} to submitted")
        except (RuntimeError, OperationError) as e:
            self.logger.error(msg=f"Failed to create multisig and broadcast, error: {e}")

    def _create_multisig(self, unsigned_tx: str, signatures: List[str]) -> str:
        """Takes all the signatures of the signers from the db and generates the signed tx with them."""

        # creates temp-files containing the signatures, as the 'multisign' command requires files as input
        with temp_file(unsigned_tx) as unsigned_tx_path:
            with temp_files(signatures, self.logger) as signed_tx_paths:
                return multisig_tx(unsigned_tx_path, self.multisig_name, *signed_tx_paths)

    @staticmethod
    def _broadcast(signed_tx) -> str:
        # Note: This operation costs Scrt
        with temp_file(signed_tx) as signed_tx_path:
            return json.loads(broadcast(signed_tx_path))['txhash']

    def _broadcast_validation(self, document: Swap):  # pylint: disable=unused-argument
        """validation of submitted broadcast signed tx

        **kwargs needs to be here even if unused, because this function gets passed arguments from mongo internals
        """
        if not document.status == Status.SWAP_SUBMITTED:
            return

        tx_hash = document.dst_tx_hash
        try:
            res = query_data_success(tx_hash)

            if res and res["mint_from_ext_chain"]["status"] == "success":
                document.update(status=Status.SWAP_CONFIRMED)
            else:
                # maybe the block took a long time - we wait 60 seconds before we mark it as failed
                if (datetime.utcnow() - document.updated_on).total_seconds() < BROADCAST_VALIDATION_COOLDOWN:
                    return
                document.update(status=Status.SWAP_FAILED)
                self.logger.critical(f"Failed confirming broadcast for tx: {document}")
        except (IndexError, json.JSONDecodeError, RuntimeError) as e:
            self.logger.critical(f"Failed confirming broadcast for tx: {document}. Error: {e}")
            # This can fail, but if it does we want to crash - this can lead to duplicate amounts and confusion
            # Better to just stop and make sure everything is kosher before continuing
            document.update(status=Status.SWAP_FAILED)
