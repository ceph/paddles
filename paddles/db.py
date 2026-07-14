from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool


# Listeners:
# @event.listens_for(mapper, 'init')
# def auto_add(target, args, kwargs):
#     Session.add(target)


def get_engine(sqlalchemy_url: str, **options) -> Engine:
    if sqlalchemy_url.startswith("sqlite"):
        options = {**options, "poolclass": NullPool}
    else:
        options = {"max_overflow": -1, **options}
    engine = create_engine(sqlalchemy_url, **options)
    if sqlalchemy_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def do_connect(dbapi_connection, connection_record):
            dbapi_connection.isolation_level = None

            # FORCE WAL MODE: Allows concurrent reading and writing seamlessly
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()

        @event.listens_for(engine, "begin")
        def do_begin(conn):
            conn.exec_driver_sql("BEGIN EXCLUSIVE")

    return engine


def get_session(engine: Engine) -> Session:
    return sessionmaker(bind=engine, expire_on_commit=False)()
