from datetime import datetime
from paddles.tests import TestApp
from paddles.util import local_datetime_to_utc
from paddles.models import Run, Job, start, commit


class TestJobsController(TestApp):
    def teardown_method(self, meth):
        start()
        Job.query.delete()
        Run.query.delete()
        commit()

    def test_get_root(self):
        response = self.app.get('/')
        assert response.status_int == 200

    def test_get_some_jobs_back(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            user="user1",
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
            status="queued",
        ))
        response = self.app.post_json(
            '/runs/foo/jobs/',
            dict(status="queued"),
        )
        assert response.status_code == 200

    def test_allows_waiting_status(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            status="waiting",
        ))
        response = self.app.get('/runs/foo/jobs/1/')
        job = response.json
        assert job["status"] == 'waiting'

    def test_to_get_newly_created_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            status="waiting",
        ))
        self.app.post_json(
            '/runs/foo/jobs/',
            dict(status="waiting"),
        )
        response = self.app.get('/runs/foo/jobs/2/')
        assert response.status_code == 200

    def test_update_a_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            user='user1'
        ))
        self.app.post_json(
            '/runs/foo/jobs/',
            dict(user='user2"'),
        )
        response = self.app.put_json(
            '/runs/foo/jobs/2/',
            dict(user='user1'),
        )
        assert response.status_code == 200

    def test_create_run_if_it_does_not_exist(self):
        self.app.post_json('/runs/bar/jobs/', dict(
            user='user1',
        ))
        response = self.app.get('/runs/bar/jobs/1/')
        assert response.json['job_id'] == '1'

    def test_slice_valid(self):
        self.app.post_json('/runs/foo/jobs/', dict(user='user1'))
        response = self.app.get('/runs/foo/jobs/?fields=job_id')
        assert response.json == [dict(
            job_id='1',
        )]

    def test_status_dead_ignored_by_completed_job(self):
        self.app.post_json('/runs/RUN/jobs/', dict(success=False,
                                                   status='fail'))
        self.app.put_json('/runs/RUN/jobs/1/', dict(status='dead'))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'fail'

    def test_status_dead_not_ignored_by_running_job(self):
        self.app.post_json('/runs/RUN/jobs/', dict(user='tester'))
        self.app.put_json('/runs/RUN/jobs/1/', dict(status='dead'))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'dead'

    def test_null_success_means_null_status(self):
        self.app.post_json('/runs/RUN/jobs/', dict(user='tester'))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'unknown'

    def test_success_true_means_status_pass(self):
        self.app.post_json('/runs/RUN/jobs/', dict(success=True))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'pass'

    def test_success_false_means_status_fail(self):
        self.app.post_json('/runs/RUN/jobs/', dict(success=False))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'fail'

    def test_status_dead_means_success_null(self):
        self.app.post_json('/runs/RUN/jobs/', dict(status='dead'))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('success') is None

    def test_status_dead_success_false_means_status_dead(self):
        self.app.post_json('/runs/RUN/jobs/',
                           dict(success=False, status='dead'))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'dead'

    def test_status_dead_success_false_means_status_dead_repost(self):
        self.app.post_json('/runs/RUN/jobs/',
                           dict(user='tester',))
        response = self.app.get('/runs/RUN/jobs/1/')
        self.app.put_json('/runs/RUN/jobs/1/',
                          dict(status='running'))
        self.app.put_json('/runs/RUN/jobs/1/',
                          dict(success=False, status='dead'))
        self.app.put_json('/runs/RUN/jobs/1/',
                          dict(success=False, status='dead'))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'dead'

    def test_status_dead_success_false_means_status_dead_repost_2(self):
        self.app.post_json('/runs/RUN/jobs/',
                           dict(user='tester',))
        response = self.app.get('/runs/RUN/jobs/1/')
        self.app.put_json('/runs/RUN/jobs/1/',
                          dict(status='running'))
        self.app.put_json('/runs/RUN/jobs/1/',
                          dict(success=False, status='dead'))
        self.app.put_json('/runs/RUN/jobs/1/',
                          dict(status='dead'))
        response = self.app.get('/runs/RUN/jobs/1/')
        assert response.json.get('status') == 'dead'

    def test_manual_updated_time(self):
        time_stamp = '2014-03-31 21:25:43'
        run_name = 'manual_update'
        self.app.post_json('/runs/', dict(name=run_name))
        self.app.post_json('/runs/%s/jobs/' % run_name, dict(
            updated=time_stamp,
        ))
        local_dt = datetime.fromisoformat(time_stamp)
        utc_dt = local_datetime_to_utc(local_dt)
        response = self.app.get('/runs/%s/jobs/%s/' % (run_name, 1))
        assert response.json['updated'] == str(utc_dt)

    def test_filter_running_jobs(self):
        self.app.post_json('/runs/filter_running/jobs/',
                           dict(status='running'))
        self.app.post_json('/runs/filter_running/jobs/',
                           dict(status='running'))
        self.app.put_json('/runs/filter_running/jobs/1/',
                          dict(success=True, status='pass'))
        response = self.app.get('/runs/filter_running/jobs/?status=running')
        assert len(response.json) == 1
