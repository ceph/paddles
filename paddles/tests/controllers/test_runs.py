from paddles.models import Run
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

    def test_get_invalid_url_on_run(self):
        response = self.app.get('/runs/suck/', expect_errors=True)
        assert response.status_int == 404
        assert response.json == {'message': 'requested job resource does not exist'}

    def test_post_valid_body(self):
        response = self.app.post_json('/runs/', dict(name="foo"))
        assert response.status_int == 200
        assert response.json == {}

    def test_create_new_run(self):
        self.app.post_json('/runs/', dict(name="foo"))
        new_run = Run.get(1)
        assert new_run.name == 'foo'

    def test_create_then_get_new_run(self):
        self.app.post_json('/runs/', dict(name="foo"))
        response = self.app.get('/runs/')
        result = response.json[0]
        assert result['name'] == 'foo'
        assert result['results'] == {'fail': 0, 'pass': 0, 'running': 0}

    def test_no_json_posted(self):
        # this is just posting a dict in the body, no proper headers
        response = self.app.post('/runs/', dict(), expect_errors=True)
        assert response.status_int == 400
        assert response.json['message'] == 'could not decode JSON body'
