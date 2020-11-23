from typing import Iterable

from src.base import EgressLeader, SwapEvent
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.ethereum.event_listener import EventTracker
from src.util.config import Config
from src.util.crypto_store.crypto_manager import CryptoManagerBase


class EthEgressLeader(EgressLeader):
    def __init__(
        self,
        multisig_contract: MultisigWallet,
        signer: CryptoManagerBase,
        config: Config,
    ):
        super().__init__(config)
        self._multisig_contract = multisig_contract
        self._signer = signer
        self._event_tracker = EventTracker(multisig_contract, ['Withdraw', 'WithdrawFailure'], config.eth_confirmations)

    # @staticmethod
    # def should_continue():
    #     """Override this to set custom stop conditions"""
    #     return True

    def native_coin_name(self) -> str:
        return "ETH"

    def get_new_swap_events(self) -> Iterable[SwapEvent]:
        """Leads the signers responsible for swaps out of the Secret Network"""
        pass

    def check_remaining_gas(self):
        """Should check that there are enough funds to keep running for a while.

        Otherwise, raise a warning (log, email, etc).
        The threshold should be set high enough to give the operator time to "refuel" the managing account.
        """
        pass

    def handle_native_swap(self, swap_event: SwapEvent):
        """This should handle swaps from the secret version of a native coin, back to the native coin"""
        pass

    def handle_non_native_swap(self, swap_event: SwapEvent):
        """This should handle swaps from the secret version of a non-native coin, back to the non-native coin

        An example of a non-native coin would be an ERC-20 coin.
        """
        pass
