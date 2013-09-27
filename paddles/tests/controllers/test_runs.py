from paddles.tests import TestApp


class TestRunController(TestApp):

    def test_get_root(self):
        response = self.app.get('/')
        assert response.status_int == 200

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404

    def test_post_invalid(self):
        response = self.app.post_json('/runs/', dict(), expect_errors=True)
        assert response.status_int == 400

    def test_post_valid_body(self):
        response = self.app.post_json('/runs/', dict(name="foo"))
        assert response.status_int == 200
        assert response.json == {}

