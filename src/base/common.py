from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import enum


# Supported networks are networks that have full support.
# Coins deployed on the networks will be named by a string.
# The native coin must be named appropriately, by its main denomination ('ETH', 'BTC', etc.)
class Network(Enum):
    Ethereum = 'Ethereum'
    Bitcoin = 'Bitcoin'


class SwapDirection(Enum):
    ToSecretNetwork = enum.auto()
    FromSecretNetwork = enum.auto()


@dataclass
class SwapEvent:
    id: str  # arbitrary ID determined by the underlying implementation
    # details
    amount: int
    decimals: int
    sender: str  # address in source network
    recipient: str  # address in destination network
    # routing
    network_name: Network
    coin_name: str
    direction: SwapDirection


# is this a good idea? or needed?
class CoinInfo(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def decimals(self) -> int:
        pass

    @property
    @abstractmethod
    def address(self) -> str:
        pass
