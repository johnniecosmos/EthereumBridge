from subprocess import CalledProcessError
from threading import Event, Thread

from web3 import Web3

import src.contracts.ethereum.message as message
from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.secret.secret_contract import swap_query_res
from src.db.collections.management import Management, Source
from src.util.logger import get_logger
from src.util.secretcli import query_scrt_swap


class EthrLeader:
    """Broadcasts signed transactions Scrt -> Ethr"""

    def __init__(self, provider: Web3, multisig_wallet: MultisigWallet, private_key, acc_addr, config):
        self.provider = provider
        self.config = config
        self.multisig_wallet = multisig_wallet
        self.private_key = private_key
        self.default_account = acc_addr
        self.logger = get_logger(db_name=self.config.db_name, logger_name=self.config.logger_name)
        self.stop_event = Event()

        # metadata that is used to allow withdraw from 3rd party erc20 contract
        self.mint_token: bool = self.config.mint_token
        if self.mint_token:
            self.token_contract = Erc20(provider, config.token_contract_addr, self.multisig_wallet.address)

        Thread(target=self._scan_swap).start()

    def _scan_swap(self):
        """ Scans secret network contract for swap events """
        current_nonce = Management.last_processed(Source.scrt.value, self.logger)
        doc = Management.objects(nonce=current_nonce, src=Source.scrt.value).get()
        next_nonce = current_nonce + 1

        while not self.stop_event.is_set():
            try:
                swap_data = query_scrt_swap(next_nonce, self.config.secret_contract_address,
                                            self.config.viewing_key)
                self._handle_swap(swap_data)
                doc.nonce = next_nonce
                doc.save()
                next_nonce += 1
                continue

            except CalledProcessError as e:
                if e.stderr != b'ERROR: query result: encrypted: Tx does not exist\n':
                    self.logger.error(msg=e.stdout + e.stderr)

            self.stop_event.wait(self.config.default_sleep_time_interval)

    def _handle_swap(self, swap_data: str):
        # Note: This operation costs Ethr
        try:
            swap_json = swap_query_res(swap_data)

            data = b""
            if self.mint_token:  # dealing with token to token transfer
                # Note: if token is to-be-swapped, the destination function name HAS to have the following signature
                # transfer(address to, uint256 value)
                data = self.token_contract.contract_tx_as_bytes('transfer',
                                                                swap_json['destination'],
                                                                int(swap_json['amount']),
                                                                b"")
                msg = message.Submit(self.token_contract.address,
                                     0,  # if we are swapping token, no ethr should be rewarded
                                     int(swap_json['nonce']), data)
            else:  # dealing with token to ethr transfer
                msg = message.Submit(swap_json['destination'], int(swap_json['amount']), int(swap_json['nonce']), data)
            tx_hash = self.multisig_wallet.submit_transaction(self.default_account, self.private_key, msg)
            self.logger.info(msg=f"Submitted tx, tx hash: {tx_hash.hex()}, msg: {msg}")

        except Exception as e:
            self.logger.error(msg=f"Failed swap, transaction data: {swap_data}. Error: {e}")
