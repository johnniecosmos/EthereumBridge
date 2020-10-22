import base64
from subprocess import CalledProcessError
from threading import Event, Thread
from typing import Dict

import src.contracts.ethereum.message as message
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.secret.secret_contract import swap_query_res
from src.db.collections.swaptrackerobject import SwapTrackerObject
from src.util.common import Token
from src.util.config import Config
from src.util.logger import get_logger
from src.util.secretcli import query_scrt_swap
from src.util.web3 import erc20_contract


class EtherLeader(Thread):
    """
    secretETH --> Swap TX --> ETH

    On Ethereum the leader monitors the sETH Secret Contract. When it sees a new swap, it will
    broadcast a submit transaction on-chain.

    The account set here must have enough ETH for all the transactions you're planning on doing
    """

    def __init__(self, multisig_wallet: MultisigWallet, private_key: bytes, account: str,
                 token_map: Dict[str, Token],
                 config: Config, **kwargs):
        self.config = config
        self.multisig_wallet = multisig_wallet

        self.erc20 = erc20_contract()

        self.private_key = private_key
        self.default_account = account
        self.tracked_tokens = token_map.keys()
        self.token_map = token_map
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

        while not self.stop_event.is_set():
            try:
                for address in self.tracked_tokens:
                    doc = SwapTrackerObject.get_or_create(src=address)
                    next_nonce = doc.nonce + 1

                    swap_data = query_scrt_swap(next_nonce, address)
                    self._handle_swap(swap_data, self.token_map[address].address)
                    doc.nonce = next_nonce
                    doc.save()
                    next_nonce += 1
                continue

            except CalledProcessError as e:
                if e.stderr != b'ERROR: query result: encrypted: AppendStorage access out of bounds\n':
                    if b'ERROR: query result: encrypted: Failed to get swap for key' not in e.stderr:
                        self.logger.error(f"Failed to query swap: stdout: {e.stdout} stderr: {e.stderr}")

            self.stop_event.wait(self.config['sleep_interval'])

    def _handle_swap(self, swap_data: str, token: str):
        # Note: This operation costs Ethr
        # disabling this for now till I get a feeling for what can fail
        # try:
        swap_json = swap_query_res(swap_data)

        if token == 'native':
            data = b""

            dest_address = base64.b64decode(swap_json['destination']).decode()

            # use address(0) for native ethereum
            msg = message.Submit(dest_address, int(swap_json['amount']), int(swap_json['nonce']),
                                 '0x0000000000000000000000000000000000000000', data)

            self._broadcast_transaction(msg)
        else:
            # encodeABI(fn_name=fn_name, args=[*args]).encode()
            self.erc20.address = token
            address = base64.standard_b64decode(swap_json['destination']).decode()
            print(f"{swap_json=}")
            data = self.erc20.encodeABI(fn_name='transfer', args=[address, int(swap_json['amount'])])
            msg = message.Submit(token,
                                 0,  # if we are swapping token, no ether should be rewarded
                                 int(swap_json['nonce']),
                                 token,
                                 data)

            print(f"{msg=}")
            self._broadcast_transaction(msg)

    def _broadcast_transaction(self, msg: message.Submit):
        tx_hash = self.multisig_wallet.submit_transaction(self.default_account, self.private_key, msg)
        self.logger.info(msg=f"Submitted tx, tx hash: {tx_hash.hex()}, msg: {msg}")
