class TestRootController:
    def test_get_root(self, app):
        response = app.get('/')
        assert response.status_int == 200

    def test_get_not_found(self, app):
        response = app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404
        assert response.content_type == 'application/json'
        assert 'message' in response.json

