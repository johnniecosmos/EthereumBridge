import src.contracts.ethereum.message as message
from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.secret.secret_contract import swap_query_res
from src.leader.eth.leader import EtherLeader
from src.util.common import Token
from src.util.config import Config
from src.util.web3 import w3


class ERC20Leader(EtherLeader):  # pylint: disable=too-many-instance-attributes
    """ Broadcasts signed ERC20 minting transfers after successful Secret-20 swap event """

    def __init__(self, multisig_wallet: MultisigWallet, token: Token, private_key, account, config: Config):
        print('ERC20Leader.__init__\n')
        self.token_contract = Erc20(w3,
                                    token,
                                    multisig_wallet.address)
        super().__init__(multisig_wallet, private_key, account, config)

    def _handle_swap(self, swap_data: str):
        # Note: This operation costs Ether
        # disabling this for now till I get a feeling for what can fail
        # try:
        swap_json = swap_query_res(swap_data)

        # Note: if token is swapped, the destination function name HAS to have the following signature
        # transfer(address to, uint256 value)
        data = self.token_contract.transaction_raw_bytes('transfer',
                                                         swap_json['destination'],
                                                         int(swap_json['amount']),
                                                         b"")
        msg = message.Submit(self.token_contract.address,
                             0,  # if we are swapping token, no ether should be rewarded
                             int(swap_json['nonce']),
                             data)

        self._broadcast_transaction(msg)
