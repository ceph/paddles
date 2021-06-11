from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.orm import scoped_session, sessionmaker, object_session, mapper
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.interfaces import PoolListener
from sqlalchemy.exc import InvalidRequestError, OperationalError
from sqlalchemy.pool import Pool
from pecan import conf

from paddles.controllers import error


class _EntityBase(object):
    """
    A custom declarative base that provides some Elixir-inspired shortcuts.
    """

    @classmethod
    def filter_by(cls, *args, **kwargs):
        return cls.query.filter_by(*args, **kwargs)

    @classmethod
    def get(cls, *args, **kwargs):
        return cls.query.get(*args, **kwargs)

    def flush(self, *args, **kwargs):
        object_session(self).flush([self], *args, **kwargs)

    def delete(self, *args, **kwargs):
        object_session(self).delete(self, *args, **kwargs)

    def as_dict(self):
        return dict((k, v) for k, v in self.__dict__.items()
                    if not k.startswith('_'))

    def slice(self, fields_str):
        sep = ','
        fields = fields_str.strip(sep).split(sep)

        obj_slice = dict()
        for field in fields:
            if field.startswith('_'):
                continue
            value = getattr(self, field)
            if callable(value):
                continue
            obj_slice[field] = value
        return obj_slice


Session = scoped_session(sessionmaker())
metadata = MetaData()
Base = declarative_base(cls=_EntityBase)
Base.query = Session.query_property()


# Listeners:

@event.listens_for(mapper, 'init')
def auto_add(target, args, kwargs):
    Session.add(target)


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
    conf.sqlalchemy.engine = _engine_from_config(conf.sqlalchemy)
    config = dict(conf.sqlalchemy)
    if 'sqlite' in config['url']:
        event.listen(Pool, 'connect', sqlite_connect, named=True)


def sqlite_connect(**kw):
    dbapi_con = kw['dbapi_connection']
    dbapi_con.execute('PRAGMA journal_mode=MEMORY')
    dbapi_con.execute('PRAGMA synchronous=OFF')


def _engine_from_config(configuration):
    configuration = dict(configuration)
    url = configuration.pop('url')
    return create_engine(url, **configuration)


def bind(engine):
    Session.bind = engine
    metadata.bind = engine


def start(isolation_level=None):
    if isolation_level:
        bind(conf.sqlalchemy.engine.execution_options(
            isolation_level=isolation_level))
    else:
        bind(conf.sqlalchemy.engine)


def start_read_only():
    bind(conf.sqlalchemy.engine)


def commit():
    try:
        Session.commit()
    except (OperationalError, InvalidRequestError):
        rollback()
        error('/errors/unavailable', 'encountered a DB error; please retry')


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
