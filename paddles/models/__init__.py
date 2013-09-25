from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.orm import scoped_session, sessionmaker, object_session, mapper
from sqlalchemy.ext.declarative import declarative_base
from pecan import conf


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


def _engine_from_config(configuration):
    configuration = dict(configuration)
    url = configuration.pop('url')
    return create_engine(url, **configuration)


def start():
    Session.bind = conf.sqlalchemy.engine
    metadata.bind = Session.bind


def start_read_only():
    Session.bind = conf.sqlalchemy.engine
    metadata.bind = Session.bind


def commit():
    Session.commit()


def rollback():
    Session.rollback()


def clear():
    Session.remove()


from runs import Run
