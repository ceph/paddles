from pecan.util import _cfg


def isolation_level(level=None):
    """
    Set an isolation_level for requests using a controller method by applying
    this decorator.

    See http://docs.sqlalchemy.org/en/latest/core/connections.html
    """
    def deco(f):
        _cfg(f)['isolation_level'] = level
        return f
    return deco
