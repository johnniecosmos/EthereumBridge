import base64
from subprocess import CalledProcessError
from threading import Event, Thread

import src.contracts.ethereum.message as message
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.secret.secret_contract import swap_query_res
from src.db.collections.management import Management, Source
from src.util.logger import get_logger
from src.util.secretcli import query_scrt_swap
from src.util.config import Config


class EtherLeader(Thread):
    """
    secretETH --> Swap TX --> ETH

    On Ethereum the leader monitors the sETH Secret Contract. When it sees a new swap, it will
    broadcast a submit transaction on-chain.

    The account set here must have enough ETH for all the transactions you're planning on doing
    """

    def __init__(self, multisig_wallet: MultisigWallet, private_key: bytes, account: str, config: Config, **kwargs):
        self.config = config
        self.multisig_wallet = multisig_wallet
        self.private_key = private_key
        self.default_account = account
        self.logger = get_logger(db_name=self.config['db_name'],
                                 logger_name=config.get('logger_name', self.__class__.__name__))
        self.stop_event = Event()
        super().__init__(group=None, name="EtherLeader", target=self.run, **kwargs)

    def stop(self):
        self.logger.info("Stopping")
        self.stop_event.set()

    def run(self):
        self.logger.info("Starting")
        self._scan_swap()

    def _scan_swap(self):
        """ Scans secret network contract for swap events """
        current_nonce = Management.last_processed(Source.SCRT.value)
        doc = Management.objects(nonce=current_nonce, src=Source.SCRT.value).get()
        next_nonce = current_nonce + 1

        while not self.stop_event.is_set():
            try:
                swap_data = query_scrt_swap(next_nonce, self.config['secret_swap_contract_address'])
                self._handle_swap(swap_data)
                doc.nonce = next_nonce
                doc.save()
                next_nonce += 1
                continue

            except CalledProcessError as e:
                if e.stderr != b'ERROR: query result: encrypted: AppendStorage access out of bounds\n':
                    self.logger.error(e.stdout + e.stderr)

            self.stop_event.wait(self.config['sleep_interval'])

    def _handle_swap(self, swap_data: str):
        # Note: This operation costs Ethr
        # disabling this for now till I get a feeling for what can fail
        # try:
        swap_json = swap_query_res(swap_data)

        data = b""

        dest_address = base64.b64decode(swap_json['destination']).decode()

        msg = message.Submit(dest_address, int(swap_json['amount']), int(swap_json['nonce']), data)

        self._broadcast_transaction(msg)

    def _broadcast_transaction(self, msg: message.Submit):
        tx_hash = self.multisig_wallet.submit_transaction(self.default_account, self.private_key, msg)
        self.logger.info(msg=f"Submitted tx, tx hash: {tx_hash.hex()}, msg: {msg}")
