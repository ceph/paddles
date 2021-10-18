from pecan.util import _cfg
from sqlalchemy.exc import OperationalError
import paddles.models
import logging

log = logging.getLogger(__name__)


def isolation_level(level=None):
    """
    Set an isolation_level for requests using a controller method by applying
    this decorator.

    See http://docs.sqlalchemy.org/en/latest/core/connections.html
    """

    def deco(f):
        _cfg(f)["isolation_level"] = level
        return f

    return deco


def retryOperation(func=None, *, attempts=10, exceptions=(OperationalError,)):
    exceptions = tuple(exceptions)

    def decorator(func):
        def wrapper(*args, **kwargs):
            _attempts = attempts
            while _attempts > 0:
                try:
                    result = func(*args, **kwargs)
                    return result
                except exceptions:
                    _attempts -= 1
                    if _attempts <= 0:
                        log.error(f"All {attempts} attempts failed: {func} with {args} {kwargs}")
                        raise
                    paddles.models.Session.rollback()

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)
