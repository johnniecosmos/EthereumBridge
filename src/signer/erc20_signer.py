from web3 import Web3

from src.signer.ether_signer import EtherSigner
from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.ethereum.event_listener import EventListener
from src.util.config import Config


class ERC20Signer(EtherSigner):
    """Verifies Secret swap tx and adds it's confirmation to the smart contract

    Signs on the ETH side, after verifying SCRT tx stored in the db
    """

    def __init__(self,
                 event_listener: EventListener,
                 multisig_wallet: MultisigWallet,
                 private_key: bytes,
                 acc_addr: str,
                 config: Config):
        self.token_contract = Erc20(Web3(Web3.HTTPProvider(config['eth_node_address'])),
                                    config['token_contract_addr'],
                                    self.multisig_wallet.address)
        super().__init__(event_listener, multisig_wallet, private_key, acc_addr, config)

    def _check_tx_data(self, swap_data: dict, submission_data: dict) -> bool:
        """
        This used to verify secret-20 <-> erc-20 tx data
        :param swap_data: the data from scrt contract query
        :param submission_data: the data from the proposed tx on the smart contract
        """
        if int(submission_data['value']) != 0:  # sanity check
            self.logger.critical(msg=f"Trying to swap ethr while swap_token flag is true. "
                                     f"Tx: {swap_data['ethr_tx_hash']}")
            return False

        addr, amount = self.token_contract.decode_encodeAbi(submission_data['data'])
        return addr.lower() == swap_data['destination'].lower() and amount == int(swap_data['amount'])
