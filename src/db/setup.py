from contextlib import contextmanager

import mongoengine


@contextmanager
def database(db="test_db", host='localhost', port=27017, username=None, password=None):
    alias = f"{db}-{host}-{port}"
    yield mongoengine.connect(
        alias=alias,
        db=db,
        host=host,
        port=port,
        username=username,
        password=password,
    )

    mongoengine.disconnect(alias)


def connect_default():
    mongoengine.connect(db="tempdb")
