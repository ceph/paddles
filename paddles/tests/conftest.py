import os
import pathlib
import pytest

from pecan import configuration
from pecan.testing import load_test_app
from sqlalchemy import Engine, Connection
from sqlalchemy.orm import sessionmaker, Session
from typing import Iterator
from uuid import uuid1

from paddles import db
from paddles.hooks.session import SessionHook
from paddles.models import Base


def pytest_addoption(parser):
    parser.addoption(
        "--db-server",
        action="store",
        help="(Optional) The URL of a running server to test against",
    )
    parser.addoption(
        "--paddles-server",
        action="store",
        help="(Optional) The URL of a running paddles server to run integration tests against",
    )


@pytest.fixture(scope="session")
def db_server_url(request) -> str:
    return request.config.getoption("--db-server")

@pytest.fixture(scope="session")
def paddles_server_url(request) -> str:
    if not (url := request.config.getoption("--paddles-server")):
        pytest.skip("No paddles server")
    return url


@pytest.fixture(scope="function")
def config_file() -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, "config.py")


@pytest.fixture(scope="function")
def temp_dir(tmp_path_factory) -> pathlib.Path:
    return tmp_path_factory.mktemp(basename="paddles-test-db", numbered=True)


@pytest.fixture(scope="function")
def temp_db_path(temp_dir) -> Iterator[pathlib.Path]:
    temp_db_path = temp_dir / "test.sqlite"
    yield temp_db_path
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture(scope="function")
def temp_db_url(temp_db_path) -> str:
    return "sqlite:///" + str(temp_db_path)


@pytest.fixture(scope="function")
def db_url(temp_db_url, db_server_url) -> str:
    return db_server_url or temp_db_url


@pytest.fixture(scope="function")
def config(config_file, db_url) -> dict:
    config = configuration.conf_from_file(config_file).to_dict()
    config["sqlalchemy"]["url"] = db_url
    return config


@pytest.fixture(scope="function")
def db_engine(db_url) -> Iterator[Engine]:
    engine = db.get_engine(db_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_connection(db_engine: Engine) -> Iterator[Connection]:
    connection = db_engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="function")
def session_factory(db_connection: Connection) -> Iterator[sessionmaker]:
    transaction = db_connection.begin()
    yield sessionmaker(bind=db_connection)
    if not transaction._deactivated_from_connection:
        transaction.rollback()


@pytest.fixture(scope="function")
def session(session_factory) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture(scope="function")
def app(config, session_factory, monkeypatch):
    monkeypatch.setattr(SessionHook, "session_factory", session_factory)
    app = load_test_app(config)
    yield app


@pytest.fixture
def job_conf_no_id():
    """
    A minimal job config object, without job_id
    """
    return {
        "name": "name",
        "machine_type": "mtype",
        "os_type": "OS",
        "os_version": "version",
    }


@pytest.fixture
def job_conf(job_conf_no_id):
    """
    A minimal job config object, with job_id
    """
    return job_conf_no_id | {"job_id": "1"}


@pytest.fixture(scope="function")
def uuid():
    yield uuid1()


@pytest.fixture(scope="function")
def name(uuid):
    yield str(uuid)
