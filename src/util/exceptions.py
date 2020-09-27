from logging import Logger, ERROR
from typing import Tuple, Callable


def catch_and_log(logger: Logger, callable_: Callable, *args, **kwargs) -> Tuple[any, bool]:
    try:
        return callable_(*args, **kwargs), True
    except Exception as e:
        logger.log(level=ERROR, msg=f"Executed function: {callable_}. Error:{e}")
        return None, False
