from contextlib import contextmanager

import mongoengine


@contextmanager
def database(db="test_db", host='localhost', username=None, password=None):
    # alias = f"{db}-{host}-{username}"

    DB_URI = f"mongodb+srv://{username}:{password}@{host}/{db}?retryWrites=true&w=majority"

    yield mongoengine.connect(
        host=DB_URI
    )

    mongoengine.disconnect()


def connect_default():
    mongoengine.connect(db="tempdb")
