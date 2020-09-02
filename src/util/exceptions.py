from typing import Tuple, Callable

from src.db.collections.log import Logs


def catch_and_log(callable: Callable, *args, **kwargs) -> Tuple[any, bool]:
    try:
        return callable(*args, **kwargs), True
    except Exception as e:
        Logs(log=repr(e)).save()
        return None, False
