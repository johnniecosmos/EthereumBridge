from event_listener import EventListener
from events import events


class Validator:
    def __init__(self, event_listner: EventListener):
        event_listner.register(events)
