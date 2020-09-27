from mongoengine import connect


def connect_default():
    connect(db="tempdb")
