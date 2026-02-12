import logging

import sqlalchemy
from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.exc import IntegrityError, InvalidRequestError, OperationalError
from sqlalchemy.orm import (
    DeclarativeBase,
    scoped_session,
    sessionmaker,
)
from sqlalchemy.pool import Pool

from paddles import conf

# from paddles.controllers import error

log = logging.getLogger(__name__)

TEUTHOLOGY_TIMESTAMP_FMT = "%Y-%m-%d_%H:%M:%S"

Session = scoped_session(sessionmaker())
metadata = MetaData()


class Base(DeclarativeBase):
    def slice(self, fields_str):
        sep = ","
        fields = fields_str.strip(sep).split(sep)

        obj_slice = dict()
        for field in fields:
            if field.startswith("_"):
                continue
            value = getattr(self, field)
            if callable(value):
                continue
            obj_slice[field] = value
        return obj_slice


# Listeners:
# @event.listens_for(mapper, 'init')
# def auto_add(target, args, kwargs):
#     Session.add(target)


def sqlite_connect(**kw):
    dbapi_con = kw["dbapi_connection"]
    dbapi_con.execute("PRAGMA journal_mode=MEMORY")
    dbapi_con.execute("PRAGMA synchronous=OFF")


def get_engine(sqlalchemy_url: str) -> sqlalchemy.Engine:
    engine = create_engine(sqlalchemy_url)
    if "sqlite" in sqlalchemy_url:
        event.listen(Pool, "connect", sqlite_connect, named=True)
    return engine


engine = get_engine(conf["sqlalchemy"]["url"])


def init_model():
    """
    This is a stub method which is called at application startup time.

    If you need to bind to a parse database configuration, set up tables or
    ORM classes, or perform any database initialization, this is the
    recommended place to do it.

    For more information working with databases, and some common recipes,
    see http://pecan.readthedocs.org/en/latest/databases.html

    For creating all metadata you would use::

        Base.metadata.create_all(conf.sqlalchemy.engine)

    """
    conf["sqlalchemy"]["engine"] = engine


def bind(engine):
    Session.bind = engine.connect()
    # metadata.bind = engine


def start(isolation_level=None):
    bind(conf["sqlalchemy"]["engine"])
    # if isolation_level:
    #     bind(conf.sqlalchemy.engine.execution_options(
    #         isolation_level=isolation_level))
    # else:
    #     bind(conf.sqlalchemy.engine)


def start_read_only():
    bind(conf["sqlalchemy"]["engine"])


def commit():
    try:
        Session.commit()
    except (OperationalError, InvalidRequestError, IntegrityError):
        # rollback()
        raise
        # error("/errors/unavailable", "encountered a DB error; please retry")


def rollback():
    Session.rollback()


def clear():
    Session.remove()


def flush():
    Session.flush()


from .runs import Run  # noqa
from .jobs import Job  # noqa
from .nodes import Node  # noqa
from .queue import Queue  # noqa
