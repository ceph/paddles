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
        response = self.app.post_json('/runs/foo/jobs/', dict(),
                                      expect_errors=True)
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

    def test_slice_valid(self):
        self.app.post_json('/runs/foo/jobs/', dict(job_id='314'))
        response = self.app.get('/runs/foo/jobs/?fields=job_id')
        assert response.json == [dict(
            job_id='314',
        )]

    def test_status_dead_ignored_by_completed_job(self):
        self.app.post_json('/runs/RUN/jobs/', dict(job_id='42', success=False))
        self.app.put_json('/runs/RUN/jobs/42/', dict(status='dead'))
        response = self.app.get('/runs/RUN/jobs/42/')
        assert response.json.get('status') == 'fail'

    def test_status_dead_not_ignored_by_running_job(self):
        self.app.post_json('/runs/RUN/jobs/', dict(job_id='42'))
        self.app.put_json('/runs/RUN/jobs/42/', dict(status='dead'))
        response = self.app.get('/runs/RUN/jobs/42/')
        assert response.json.get('status') == 'dead'

    def test_null_success_means_null_status(self):
        self.app.post_json('/runs/RUN/jobs/', dict(job_id='42'))
        response = self.app.get('/runs/RUN/jobs/42/')
        assert response.json.get('status') == 'unknown'

    def test_success_true_means_status_pass(self):
        self.app.post_json('/runs/RUN/jobs/', dict(job_id='42', success=True))
        response = self.app.get('/runs/RUN/jobs/42/')
        assert response.json.get('status') == 'pass'

    def test_success_false_means_status_fail(self):
        self.app.post_json('/runs/RUN/jobs/', dict(job_id='42', success=False))
        response = self.app.get('/runs/RUN/jobs/42/')
        assert response.json.get('status') == 'fail'

    def test_status_dead_means_success_false(self):
        self.app.post_json('/runs/RUN/jobs/', dict(job_id='42', status='dead'))
        response = self.app.get('/runs/RUN/jobs/42/')
        assert response.json.get('success') == False
