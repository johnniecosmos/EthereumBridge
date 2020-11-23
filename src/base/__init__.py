from abc import ABC, abstractmethod
from time import sleep
from typing import Iterable

from src.db import Swap, Status, SwapTrackerObject
from src.util.common import Token
from src.util.config import Config
from src.util.logger import get_logger

from .common import Network, SwapEvent, SwapDirection
from .db import TokenPair


class EgressLeader(ABC):
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(
            db_name=config.db_name,
            loglevel=config.log_level,
            logger_name=config.logger_name or type(self).__name__
        )

        pairs = TokenPair.objects(network=Network.Ethereum)
        self._token_map = {}
        confirmer_token_map = {}
        for pair in pairs:
            self._token_map[pair.secret_coin_address] = Token(pair.coin_address, pair.coin_name)
            confirmer_token_map[pair.secret_coin_address] = Token(pair.coin_address, pair.coin_name)

        self._swap_tracker = {token: SwapTrackerObject.get_or_create(src=token) for token in self._token_map}

    """Leads the signers responsible for swaps to foreign networks"""
    def start(self):
        """This is the high-level entry point for the leader"""
        while True:
            swap_events = self.get_new_swap_events()
            for swap_event in swap_events:
                try:
                    self.check_remaining_gas()
                    self.handle_swap(swap_event)
                    self._store_swap(swap_event)
                except Exception:
                    self._store_failed_swap(swap_event)
            self._wait_for_updates()

    def handle_swap(self, swap_event: SwapEvent):
        if swap_event.coin_name == self.native_coin_name():
            self.handle_native_swap(swap_event)
        else:
            self.handle_non_native_swap(swap_event)

    def _store_swap(self, swap_event: SwapEvent):
        pass

    def _store_failed_swap(self, swap_event: SwapEvent):
        from pymongo.errors import DuplicateKeyError
        from mongoengine.errors import NotUniqueError

        assert swap_event.direction == SwapDirection.FromSecretNetwork

        swap = Swap(
            src_network="Secret",
            src_tx_hash=swap_event.id,
            src_coin=src_token,
            dst_coin=dst_token,
            dst_network="Ethereum",
            dst_address=swap_event.recipient,
            unsigned_tx=swap_event.data,
            amount=str(swap_event.amount),
            status=Status.SWAP_FAILED
        )
        try:
            swap.save()
        except (DuplicateKeyError, NotUniqueError):
            pass
        return

    @staticmethod
    def should_continue():
        """Override this to set custom stop conditions"""
        return True

    def _wait_for_updates(self):
        """Sleep for a while, before checking for new swap events"""
        sleep(self.config.sleep_interval)

    @abstractmethod
    def native_network(self) -> Network:
        pass

    @abstractmethod
    def native_coin_name(self) -> str:
        pass

    @abstractmethod
    def get_new_swap_events(self) -> Iterable[SwapEvent]:
        """Leads the signers responsible for swaps out of the Secret Network"""
        pass

    @abstractmethod
    def check_remaining_gas(self):
        """Should check that there are enough funds to keep running for a while.

        Otherwise, raise a warning (log, email, etc).
        The threshold should be set high enough to give the operator time to "refuel" the managing account.
        """
        pass

    @abstractmethod
    def handle_native_swap(self, swap_event: SwapEvent):
        """This should handle swaps from the secret version of a native coin, back to the native coin"""
        pass

    @abstractmethod
    def handle_non_native_swap(self, swap_event: SwapEvent):
        """This should handle swaps from the secret version of a non-native coin, back to the non-native coin

        An example of a non-native coin would be an ERC-20 coin.
        """
        pass


class EgressSigner(ABC):
    """Signs confirmations of swaps to other networks from the Secret Network"""
    def start(self):
        """Provided method - uses abstract methods to manage the swap process"""
        pass

    @abstractmethod
    def foo(self):
        pass


class IngressLeader(ABC):
    """Leads the signers responsible for swaps to the Secret Network"""
    def start(self):
        """Provided method - uses abstract methods to manage the swap process"""
        pass

    @abstractmethod
    def foo(self):
        pass


class IngressSigner(ABC):
    """Signs confirmations of swaps from other networks to the Secret Network"""
    def start(self):
        """Provided method - uses abstract methods to manage the swap process"""
        pass

    @abstractmethod
    def foo(self):
        pass
