from abc import ABC
from threading import Thread
from typing import Callable, List, Generator


class EventProvider(ABC, Thread):
    _chain: str = ''

    @property
    def chain(self):
        if not self._chain:
            raise NotImplementedError
        return self._chain

    def register(self, callback: Callable, events: List[str]):
        raise NotImplementedError

    def events_in_range(self, event: str, from_block: int, to_block: int = None) -> Generator:
        raise NotImplementedError
