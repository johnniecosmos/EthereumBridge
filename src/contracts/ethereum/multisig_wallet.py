import os
from typing import Dict

from web3 import Web3

from src.contracts.ethereum.ethr_contract import EthereumContract
from src.contracts.ethereum.message import Submit, Confirm
from src.util.common import project_base_path


class MultisigWallet(EthereumContract):
    def __init__(self, provider: Web3, contract_address: str):
        abi_path = os.path.join(project_base_path(), 'src', 'contracts', 'ethereum', 'abi', 'MultiSigSwapWallet.json')
        super().__init__(provider, contract_address, abi_path)

    def submit_transaction(self, from_: str, private_key: bytes, message: Submit):
        return self.send_transaction('submitTransaction', from_, private_key, *message.args())

    def confirm_transaction(self, from_: str, private_key: bytes, message: Confirm):
        return self.send_transaction('confirmTransaction', from_, private_key, *message.args())

    def extract_addr(self, tx_log) -> str:
        return tx_log.args.recipient.decode()

    def extract_amount(self, tx_log) -> int:
        return tx_log.args.value

    def verify_destination(self, tx_log) -> bool:
        # returns true if the Ethr was sent to the MultiSigWallet
        # noinspection PyProtectedMember
        return tx_log.address.lower() == self.address.lower()

    def verify_confirmation(self, transaction_id, account: str) -> bool:
        return self.contract.functions.confirmations(transaction_id, account).call()

    def approve_and_sign(self, key: bytes, account: str, submission_id: int) -> str:
        """
        Sign the transaction with the signer's private key and then broadcast
        Note: This operation costs gas
        """
        msg = Confirm(submission_id)
        tx_hash = self.confirm_transaction(account, key, msg)
        return tx_hash

    def submission_data(self, transaction_id) -> Dict[str, any]:
        data = self.contract.functions.transactions(transaction_id).call()
        return {'dest': data[0], 'value': data[1], 'data': data[2], 'executed': data[3], 'nonce': data[4],
                'ethr_tx_hash': transaction_id}

    @classmethod
    def tracked_event(cls) -> str:
        return 'Swap'
