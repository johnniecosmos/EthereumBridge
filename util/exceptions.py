from typing import Tuple

from db.collections.log import Logs


def catch_and_log(callable, *args, **kwargs) -> Tuple[any, bool]:
    try:
        return callable(*args, **kwargs), True
    except Exception as e:
        Logs(log=repr(e)).save()
        return None, False
