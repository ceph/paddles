from paddles.tests import TestApp


class TestJobsController(TestApp):

    def test_get_root(self):
        response = self.app.get('/')
        assert response.status_int == 200

    def test_get_some_jobs_back(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
        ))
        response = self.app.get('/runs/foo/jobs/')
        assert len(response.json) == 1
        assert response.json[0]['job_id'] == '1'
