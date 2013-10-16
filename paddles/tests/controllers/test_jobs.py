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

    def test_attempt_to_create_a_new_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
        ))
        response = self.app.post_json('/runs/foo/jobs/', dict(), expect_errors=True)
        assert response.status_code == 400

    def test_to_create_a_new_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
        ))
        response = self.app.post_json(
            '/runs/foo/jobs/',
            dict(job_id=1234),
        )
        assert response.status_code == 200

    def test_to_get_newly_created_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
        ))
        self.app.post_json(
            '/runs/foo/jobs/',
            dict(job_id=1234),
        )
        response = self.app.get('/runs/foo/jobs/1234/')
        assert response.status_code == 200

    def test_update_a_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
        ))
        self.app.post_json(
            '/runs/foo/jobs/',
            dict(job_id=1234),
        )
        response = self.app.put_json(
            '/runs/foo/jobs/1234/',
            dict(job_id=1234),
        )
        assert response.status_code == 200

    def test_create_run_if_it_does_not_exist(self):
        self.app.post_json('/runs/bar/jobs/', dict(
            job_id=13,
        ))
        response = self.app.get('/runs/bar/jobs/13/')
        assert response.json['job_id'] == '13'
