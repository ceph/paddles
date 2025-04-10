from copy import deepcopy
import os
from pecan import configuration
from pecan.testing import load_test_app
from paddles import models as pmodels
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def config_file():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, 'config.py')


class TestModel(object):

    config = configuration.conf_from_file(config_file()).to_dict()
    engine_url = config['sqlalchemy']['url']

    __db__ = None

    @classmethod
    def setup_class(cls):
        # Bind and create the database tables
        pmodels.clear()

        db_engine = create_engine(
            cls.engine_url,
            encoding='utf-8',
            poolclass=NullPool)

        # AKA models.start()
        pmodels.Base.metadata.drop_all(db_engine)
        pmodels.Session.bind = db_engine
        pmodels.metadata.bind = pmodels.Session.bind

        pmodels.Base.metadata.create_all(db_engine)
        pmodels.commit()
        pmodels.clear()

    def setup_method(self):
        config = deepcopy(self.config)

        # Add the appropriate connection string to the app config.
        config['sqlalchemy'] = {
            'url': self.engine_url,
            'encoding': 'utf-8',
            'poolclass': NullPool
        }

        # Set up a fake app
        self.app = self.load_test_app(config)
        pmodels.start()

    def load_test_app(self, config):
        return load_test_app(config)

    def teardown_method(self):
        pmodels.rollback()
        pmodels.clear()


class TestApp(TestModel):
    """
    A controller test starts a database transaction and creates a fake
    WSGI app.
    """

    __headers__ = {}

    def _do_request(self, url, method='GET', **kwargs):
        methods = {
            'GET': self.app.get,
            'POST': self.app.post,
            'POSTJ': self.app.post_json,
            'PUT': self.app.put,
            'DELETE': self.app.delete
        }
        kwargs.setdefault('headers', {}).update(self.__headers__)
        return methods.get(method, self.app.get)(str(url), **kwargs)

    def post_json(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a POST request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, 'POSTJ', **kwargs)

    def post(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a POST request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, 'POST', **kwargs)

    def get(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a GET request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, 'GET', **kwargs)

    def put(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a PUT request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, 'PUT', **kwargs)

    def delete(self, url, **kwargs):
        """
        @param (string) url - The URL to emulate a DELETE request to
        @returns (paste.fixture.TestResponse)
        """
        return self._do_request(url, 'DELETE', **kwargs)
