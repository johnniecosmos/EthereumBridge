from typing import List
from abc import abstractmethod
from event_listener import EventListener


class EventManager:
    def __init__(self, event_listener: EventListener):
        event_listener.register(self.handle)

    @abstractmethod
    def handle(self, event_logs: List[any]):
        raise NotImplementedError


class Leader(EventManager):
    def handle(self, event_logs: List[any]):
        pass


class Validator(EventManager):
    def handle(self, event_logs: List[any]):
        pass