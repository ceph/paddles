from unittest import TestCase
from webtest import TestApp
from paddles.tests import FunctionalTest


class TestRootController(FunctionalTest):

    def test_get_root(self):
        response = self.app.get('/')
        assert response.status_int == 200

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404

