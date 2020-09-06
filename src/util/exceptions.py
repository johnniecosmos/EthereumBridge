from typing import Tuple, Callable

from logging import Logger, ERROR


def catch_and_log(logger: Logger, callable: Callable, *args, **kwargs) -> Tuple[any, bool]:
    try:
        return callable(*args, **kwargs), True
    except Exception as e:
        logger.log(level= ERROR, msg=e)
        return None, False
