from logging import Logger
from typing import Tuple, Callable


def catch_and_log(logger: Logger, callable_: Callable, *args, **kwargs) -> Tuple[any, bool]:
    try:
        return callable_(*args, **kwargs), True
    except Exception as e:
        logger.error(msg=f"Executed function: {callable_}.\nError:{e}")
        return None, False
