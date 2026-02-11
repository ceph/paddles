import logging
import os

from pecan import configuration
from pecan.testing import load_test_app
from sqlalchemy import create_engine, delete
from sqlalchemy.pool import NullPool

from paddles import conf
from paddles import models as pmodels
from paddles.models.job_nodes import job_nodes_table

log = logging.getLogger(__name__)


def config_file():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, "config.py")


_config = configuration.conf_from_file(config_file()).to_dict()
_config["sqlalchemy"]["url"] = conf["sqlalchemy"]["url"]


class TestModel(object):
    config = _config
    engine_url = config["sqlalchemy"]["url"]
    db_engine = create_engine(
        engine_url,
        poolclass=NullPool,
    )

    __db__ = None

    @classmethod
    def setup_class(cls):
        pmodels.clear()
        pmodels.conf["sqlalchemy"]["engine"] = cls.db_engine
        pmodels.Base.metadata.drop_all(cls.db_engine)
        pmodels.start()
        pmodels.Base.metadata.create_all(cls.db_engine)
        pmodels.commit()
        pmodels.clear()

    def setup_method(self):
        pmodels.start()
        pmodels.Session.execute(delete(job_nodes_table))
        pmodels.Session.execute(delete(pmodels.Run))
        pmodels.Session.execute(delete(pmodels.Job))
        pmodels.Session.execute(delete(pmodels.Node))
        pmodels.Session.execute(delete(pmodels.Queue))

    def teardown_method(self):
        pmodels.rollback()
        pmodels.Session.execute(delete(job_nodes_table))
        pmodels.Session.execute(delete(pmodels.Run))
        pmodels.Session.execute(delete(pmodels.Job))
        pmodels.Session.execute(delete(pmodels.Node))
        pmodels.Session.execute(delete(pmodels.Queue))
        pmodels.commit()
        pmodels.clear()


class TestApp(TestModel):
    """
    A controller test starts a database transaction and creates a fake
    WSGI app.
    """

    __headers__ = {}

    def setup_class(self):
        super().setup_class()
        self.app = load_test_app(self.config)

    def _do_request(self, url, method="GET", **kwargs):
        methods = {
            "GET": self.app.get,
            "POST": self.app.post,
            "POSTJ": self.app.post_json,
            "PUT": self.app.put,
            "DELETE": self.app.delete,
        }
        kwargs.setdefault("headers", {}).update(self.__headers__)
        return methods.get(method, self.app.get)(str(url), **kwargs)

    def post_json(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a POST request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, "POSTJ", **kwargs)

    def post(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a POST request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, "POST", **kwargs)

    def get(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a GET request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, "GET", **kwargs)

    def put(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a PUT request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, "PUT", **kwargs)

    def delete(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a DELETE request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, "DELETE", **kwargs)
