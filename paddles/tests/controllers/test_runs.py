from pytest import skip
from pecan import conf

from paddles.models import Run, Job
from paddles.tests import TestApp


class TestRunController(TestApp):

    def test_get_root(self):
        response = self.app.get('/runs/')
        assert response.status_int == 200

    def test_get_not_found(self):
        response = self.app.get('/runs/bogus/url', expect_errors=True)
        assert response.status_int == 404

    def test_post_invalid(self):
        response = self.app.post_json('/runs/', dict(), expect_errors=True)
        assert response.status_int == 400

    def test_get_invalid_url_on_run(self):
        response = self.app.get('/runs/suck/', expect_errors=True)
        assert response.status_int == 404

    def test_post_valid_body(self):
        response = self.app.post_json('/runs/', dict(name="foo"))
        assert response.status_int == 200
        assert response.json == {}

    def test_create_new_run(self):
        self.app.post_json('/runs/', dict(name="foo"))
        new_run = Run.get(1)
        assert new_run.name == 'foo'

    def test_allows_waiting_status(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
            status="waiting",
        ))
        new_run = Run.get(1)
        assert new_run.status == 'waiting'

    def test_running_status_with_waiting_and_running_jobs(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
            status="running",
        ))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=2,
            status="waiting",
        ))
        new_run = Run.get(1)
        assert new_run.status == 'running'

    def test_create_then_get_new_run(self):
        self.app.post_json('/runs/', dict(name="foo"))
        response = self.app.get('/runs/')
        result = response.json[0]
        assert result['name'] == 'foo'

    def test_no_json_posted(self):
        # this is just posting a dict in the body, no proper headers
        response = self.app.post('/runs/', dict(), expect_errors=True)
        assert response.status_int == 400
        assert response.json['message'] == 'could not decode JSON body'

    def test_create_new_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
        ))
        new_job = Job.get(1)
        assert new_job.job_id == '1'

    def test_delete_empty_run(self):
        self.app.post_json('/runs/', dict(name='foo'))
        self.app.delete('/runs/foo/')
        response = self.app.get('/runs/foo/', expect_errors=True)
        assert response.status_int == 404

    def test_delete_full_run(self):
        self.app.post_json('/runs/', dict(name='foo'))
        self.app.post_json('/runs/foo/', dict(job_id='42'))
        self.app.post_json('/runs/foo/', dict(job_id='9'))
        self.app.post_json('/runs/foo/', dict(job_id='12345'))
        self.app.delete('/runs/foo/')
        response = self.app.get('/runs/foo/jobs/12345/', expect_errors=True)
        assert response.status_int == 404

    def test_slice_valid(self):
        self.app.post_json('/runs/', dict(name='slice_valid'))
        print self.app.get('/runs/slice_valid/').json
        response = self.app.get('/runs/?fields=name,status')
        assert response.json == [dict(
            name='slice_valid',
            status='empty',
        )]

    def test_runs_by_branch(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/branch/master/')
        assert response.json[0]['name'] == run_b_name

    def test_runs_by_suite(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/suite/rados/')
        assert response.json[0]['name'] == run_a_name

    def test_runs_by_branch_then_status(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/branch/master/status/empty/')
        print response.json
        assert response.json[0]['name'] == run_b_name

    def test_runs_by_branch_then_suite(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/branch/master/suite/big/')
        assert response.json[0]['name'] == run_b_name

    def test_runs_by_suite_then_branch(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/suite/rados/branch/next/')
        assert response.json[0]['name'] == run_a_name

    def test_get_branches(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/branch/')
        assert sorted(response.json) == ['master', 'next']

    def test_get_suites(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/suite/')
        assert sorted(response.json) == ['big', 'rados']

    def test_get_suites_since_runs_by_branch(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/branch/master/suite/')
        assert response.json == ['big']

    def test_get_machine_types(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-vps'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/machine_type/')
        assert response.json == ['plana', 'vps']

    def test_get_runs_by_machine_types(self):
        run_a_name = \
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana'
        run_b_name = \
            'teuthology-2013-01-02_00:00:00-big-master-testing-basic-vps'
        self.app.post_json('/runs/', dict(name=run_a_name))
        self.app.post_json('/runs/', dict(name=run_b_name))
        response = self.app.get('/runs/machine_type/vps/')
        assert response.json[0]['name'] == run_b_name

    def test_queued_fully(self):
        run_names = ['run_one', 'run_two']
        for run_name in run_names:
            self.app.post_json('/runs/', dict(name=run_name))
            self.app.post_json('/runs/%s/jobs/' % run_name, dict(job_id=1,
                                                            status='queued'))
            self.app.post_json('/runs/%s/jobs/' % run_name, dict(job_id=2,
                                                            status='queued'))

        result = self.app.get('/runs/queued/').json
        result_names = sorted([r['name'] for r in result])
        assert result_names == sorted(run_names)

    def test_queued_partially(self):
        run_names = ['run_one', 'run_two']
        for run_name in run_names:
            self.app.post_json('/runs/', dict(name=run_name))
            self.app.post_json('/runs/%s/jobs/' % run_name, dict(job_id=1,
                                                            status='queued'))
            self.app.post_json('/runs/%s/jobs/' % run_name, dict(job_id=2,
                                                            status='dead'))

        result = self.app.get('/runs/queued/').json
        result_names = sorted([r['name'] for r in result])
        assert result_names == sorted(run_names)


class TestRunControllerDateFilters(TestApp):

    def setup(self):
        TestApp.setup(self)
        self.day1_runs = [
            'teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana',
            'teuthology-2013-01-01_00:00:01-nfs-next-testing-basic-plana',
            'teuthology-2013-01-01_00:00:02-rados-master-testing-basic-plana',
            'teuthology-2013-01-01_00:00:03-nfs-master-testing-basic-plana',
        ]
        self.day2_runs = [
            'teuthology-2013-01-02_00:00:00-rados-next-testing-basic-plana',
            'teuthology-2013-01-02_00:00:01-nfs-next-testing-basic-plana',
            'teuthology-2013-01-02_00:00:02-rados-master-testing-basic-plana',
            'teuthology-2013-01-02_00:00:03-nfs-master-testing-basic-plana',
        ]
        self.day3_runs = [
            'teuthology-2013-01-03_00:00:00-rados-next-testing-basic-plana',
            'teuthology-2013-01-03_00:00:01-nfs-next-testing-basic-plana',
            'teuthology-2013-01-03_00:00:02-rados-master-testing-basic-plana',
            'teuthology-2013-01-03_00:00:03-nfs-master-testing-basic-plana',
        ]
        self.day4_runs = [
            'teuthology-2013-01-04_00:00:00-rados-next-testing-basic-plana',
            'teuthology-2013-01-04_00:00:01-nfs-next-testing-basic-plana',
            'teuthology-2013-01-04_00:00:02-rados-master-testing-basic-plana',
            'teuthology-2013-01-04_00:00:03-nfs-master-testing-basic-plana',
        ]
        for run in (self.day1_runs + self.day2_runs + self.day3_runs +
                    self.day4_runs):
            self.app.post_json('/runs/', dict(name=run))

    def test_date_filter_finds_runs(self):
        if 'sqlite' in conf['sqlalchemy']['url']:
            skip("sqlite does not support DATE")

        response = self.app.get('/runs/date/2013-01-02/')
        got_names = [run['name'] for run in response.json]
        assert got_names == self.day2_runs

    def test_bad_date_returns_error(self):
        response = self.app.get('/runs/date/2097-13-32/', expect_errors=True)
        assert response.json.get('message').startswith(
            'date format must match')

    def test_date_range_filter_finds_runs(self):
        response = self.app.get('/runs/date/from/2013-01-02/to/2013-01-03/')
        got_names = [run['name'] for run in response.json]
        assert sorted(got_names) == sorted(self.day2_runs + self.day3_runs)

    def test_bad_date_range_returns_error(self):
        response = self.app.get('/runs/date/from/yesterday/to/2097-13-32/',
                                expect_errors=True)
        assert response.json.get('message').startswith(
            'date format must match')

    def test_branch_and_since(self):
        response = self.app.get('/runs/branch/next/?since=2013-01-03')
        got_names = sorted(run['name'] for run in response.json)
        assert got_names == self.day3_runs[0:2] + self.day4_runs[0:2]

    def test_suite_and_since(self):
        response = self.app.get('/runs/suite/nfs/?since=2013-01-03')
        got_names = sorted(run['name'] for run in response.json)
        assert got_names == (self.day3_runs + self.day4_runs)[1::2]

    def test_suite_and_branch_and_since(self):
        response = self.app.get(
            '/runs/suite/nfs/branch/next/?since=2013-01-03')
        got_names = sorted(run['name'] for run in response.json)
        assert got_names == [self.day3_runs[1], self.day4_runs[1]]


