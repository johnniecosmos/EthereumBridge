import os
import sys
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import List

import src
from src.db.collections.log import Logs


@contextmanager
def temp_file(data: str):
    f = NamedTemporaryFile(mode="w+", delete=False)
    f.write(data)
    f.close()
    yield f.name
    os.remove(f.name)


@contextmanager
def temp_files(data: List[str]) -> List[str]:
    temp = []
    for d in data:
        temp.append(temp_file(d))

    yield list(manager.__enter__() for manager in temp)
    for manager in temp:
        try:
            manager.__exit__(*sys.exc_info())
        except OSError as e:
            Logs(log=f"Couldn't remove file: {e}")


def project_base_path():
    return os.sep.join(os.path.split(src.__file__[:-1]))
