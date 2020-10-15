from typing import Dict

from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.signer.eth.impl import EthSignerImpl
from src.contracts.ethereum.erc20 import Erc20
from src.util.common import Token
from src.util.config import Config
from src.util.web3 import web3_provider


class _ERC20SignerImpl(EthSignerImpl):
    """
    Verifies Secret swap tx and adds it's confirmation to the ERC-20 contract
    Sends the ERC-20 confirmation tx, after verifying SCRT tx stored in the db

    See EthSignerImpl for more info
    """

    def __init__(self, multisig_wallet: MultisigWallet, token: Token,
                 private_key: bytes, account: str, config: Config):
        self.token_contract = Erc20(web3_provider(config['eth_node_address']),
                                    token,
                                    multisig_wallet.address)
        super().__init__(config=config, multisig_wallet=multisig_wallet, private_key=private_key, account=account)

    def _validate_tx_data(self, swap_data: Dict, submission_data: Dict) -> bool:
        """
        This used to verify secret-20 <-> erc-20 tx data
        :param swap_data: the data from secret20 contract query
        :param submission_data: the data from the proposed tx on the smart contract
        """
        if int(submission_data['value']) != 0:  # sanity check
            self.logger.critical(f"Got an erc-20 transaction with a non-empty amount of ETH sent "
                                 f"{swap_data['ethr_tx_hash']}")
            return False
        try:
            addr, amount = self.token_contract.get_params_from_data(submission_data['data'])
            return addr.lower() == swap_data['destination'].lower() and amount == int(swap_data['amount'])
        except ValueError as e:
            self.logger.error(f"Failed to verify transaction with submission data: {submission_data} - {str(e)}")
            return False
