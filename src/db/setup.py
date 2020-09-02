#  TODO: startup script to initialize DB
from mongoengine import connect


def connect_default():
    connect(db="tempdb")
