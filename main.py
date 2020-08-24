from mongoengine import *

from event_listener import EventListener

if __name__ == "__main__":
    EventListener()
    name = connect('tumblelog')
    pass
