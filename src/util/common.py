import sys
from contextlib import contextmanager
from os import remove
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

import src


@contextmanager
def temp_file(data: str):
    f = NamedTemporaryFile(mode="w+", delete=False)
    f.write(data)
    f.close()
    yield f.name
    remove(f.name)


@contextmanager
def temp_files(data: List[str], logger) -> List[str]:
    temp = []
    for d in data:
        temp.append(temp_file(d))

    yield list(manager.__enter__() for manager in temp)
    for manager in temp:
        try:
            manager.__exit__(*sys.exc_info())
        except OSError as e:
            logger.debug(msg=e)


# noinspection PyTypeChecker
def project_base_path():
    res = module_dir(src)
    return Path(res).parent


def module_dir(module) -> str:
    return Path(module.__file__).parent
