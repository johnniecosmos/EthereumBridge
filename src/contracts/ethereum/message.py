from abc import abstractmethod
from typing import Tuple


class Message:
    @abstractmethod
    def args(self) -> Tuple:
        """converts msg attributes into args tuple"""
        pass
