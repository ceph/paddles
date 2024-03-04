from paddles.models import Job, Run
from paddles.tests import TestApp
from paddles import models
import pytz
import tzlocal

import pytest


class TestRunModel(TestApp):

    def test_jobs_count(self):
        Run.query.delete()
        Job.query.delete()
        new_run = Run('test_jobs_count')
        Job({'id':1, 'job_id':'1'}, new_run)
        Job({'id':2, 'job_id':'2'}, new_run)
        models.commit()
        run_as_json = Run.get(1).__json__()
        assert run_as_json['jobs_count'] == 2

    def test_run_deletion(self):
        run_name = 'test_run_deletion'
        new_run = Run(run_name)
        Job({'id': 3, 'job_id': '3'}, new_run)
        Job({'id': 4, 'job_id': '4'}, new_run)
        Job({'id': 5, 'job_id': '5'}, new_run)
        models.commit()
        new_run.delete()
        models.commit()
        assert not Run.filter_by(name=run_name).first()

    def test_empty_run_deletion(self):
        run_name = 'test_empty_run_deletion'
        new_run = Run(run_name)
        models.commit()
        new_run.delete()
        models.commit()
        assert not Run.filter_by(name=run_name).first()

    def test_job_deletion(self):
        run_name = 'test_job_deletion'
        new_run = Run(run_name)
        Job({'id': 6, 'job_id': '6'}, new_run)
        Job({'id': 7, 'job_id': '7'}, new_run)
        models.commit()
        new_run.delete()
        models.commit()
        assert not Job.filter_by(job_id='7').first()

    def test_scheduled(self):
        run_name = 'teuthology-2013-10-23_01:35:02-upgrade-small-next-testing-basic-vps'  # noqa
        new_run = Run(run_name)
        scheduled_aware = pytz.utc.localize(new_run.scheduled)
        localtz = tzlocal.get_localzone()
        scheduled_local = scheduled_aware.astimezone(localtz)
        scheduled_local_naive = scheduled_local.replace(tzinfo=None)
        assert str(scheduled_local_naive) == '2013-10-23 01:35:02'

    def test_updated(self):
        run_name = 'test_updated'
        new_run = Run(run_name)
        for i in range(1, 5):
            Job(dict(job_id=60+i, id=60+i), new_run)
        models.commit()
        new_run = Run.filter_by(name=run_name).first()
        assert new_run.updated == new_run.get_jobs()[-1].updated

    def test_run_slice_valid(self):
        run_name = 'test_run_slice_valid'
        new_run = Run(run_name)
        assert 'posted' in new_run.slice('posted')

    def test_run_slice_valid_many(self):
        run_name = 'test_run_slice_valid_many'
        new_run = Run(run_name)
        run_slice = new_run.slice('posted,name,status')
        assert ('posted' in run_slice and 'name' in run_slice and 'status'
                in run_slice)

    def test_run_slice_invalid(self):
        run_name = 'test_run_slice_invalid'
        new_run = Run(run_name)
        with pytest.raises(AttributeError):
            new_run.slice('bullcrap')

    def test_run_suite_typical(self):
        run_name = \
            'teuthology-2013-10-22_03:00:02-big-next-testing-basic-plana'
        new_run = Run(run_name)
        assert new_run.suite == 'big'

    def test_run_suite_hyphenated(self):
        run_name = \
            'teuthology-2013-10-22_03:00:02-ceph-deploy-next-testing-basic-plana'  # noqa
        new_run = Run(run_name)
        assert new_run.suite == 'ceph-deploy'

    def test_run_suite_weird(self):
        run_name = 'teuthology-2013-10-23_00:30:38-rgw-next---basic-saya'
        new_run = Run(run_name)
        assert new_run.suite == 'rgw'

    def test_run_suite_unlisted(self):
        run_name = \
            'teuthology-2013-10-22_03:00:02-kittens-next-testing-basic-plana'
        new_run = Run(run_name)
        assert new_run.suite == 'kittens'

    def test_run_suite_nosuite(self):
        run_name = 'whatup'
        new_run = Run(run_name)
        assert new_run.suite == ''

    def test_run_branch(self):
        run_name = \
            'teuthology-2013-10-22_03:00:02-big-next-testing-basic-plana'
        new_run = Run(run_name)
        assert new_run.branch == 'next'

    def test_run_branch_hyphenated(self):
        run_name = \
            'teuthology-2013-10-22_03:00:02-big-wip-9999-testing-basic-plana'
        new_run = Run(run_name)
        assert new_run.branch == 'wip-9999'

    def test_run_hyphenated_suite_and_branch(self):
        run_name = \
            'teuthology-2013-10-22_03:00:02-ceph-deploy-wip-9999-testing-basic-plana'  # noqa
        new_run = Run(run_name)
        assert (new_run.suite, new_run.branch) == ('ceph-deploy', 'wip-9999')

    def test_run_status_empty(self):
        run_name = "run_status_empty"
        new_run = Run(run_name)
        assert new_run.status == 'empty'

    def test_run_status_running(self):
        run_name = "run_status_running"
        new_run = Run(run_name)
        Job(dict(job_id=8, id=8, status='running'), new_run)
        Job(dict(job_id=48, id=48, status='pass'), new_run)
        assert new_run.status == 'running'

    def test_run_status_queued(self):
        run_name = "run_status_queued"
        new_run = Run(run_name)
        Job(dict(job_id=9, id=9, status='queued'), new_run)
        Job(dict(job_id=10, id=10, status='queued'), new_run)
        assert new_run.status == 'queued'

    def test_run_status_queued_to_running(self):
        run_name = "run_status_queued_to_running"
        new_run = Run(run_name)
        job = Job(dict(job_id=11, id=11, status='queued'), new_run)
        Job(dict(job_id=12, id=12, status='queued'), new_run)
        job.update(dict(status='running'))
        assert new_run.status == 'running'

    def test_run_status_running_to_dead(self):
        run_name = "run_status_running_to_dead"
        new_run = Run(run_name)
        jobs = []
        job_count = 5
        for i in range(job_count):
            jobs.append(Job(dict(job_id=20+i, id=20+i, status='running'), new_run))
        for job in jobs:
            job.update(dict(status='dead'))
        assert new_run.status == 'finished dead'

    def test_run_status_dead_to_running(self):
        run_name = "run_status_dead_to_running"
        new_run = Run(run_name)
        jobs = []
        job_count = 5
        for i in range(job_count):
            jobs.append(Job(dict(job_id=30+i, id=30+i, status='dead'), new_run))
        for job in jobs:
            job.update(dict(status='running'))
        assert new_run.status == 'running'

    def test_run_status_fail(self):
        run_name = "run_status_fail"
        new_run = Run(run_name)
        Job(dict(job_id=13, id=13, status='fail'), new_run)
        #Job(dict(job_id=13, id=13, status='pass'), new_run)
        assert new_run.status == 'finished fail'

    def test_run_status_pass(self):
        run_name = "run_status_pass"
        new_run = Run(run_name)
        Job(dict(job_id=14, id=14, status='pass'), new_run)
        #Job(dict(job_id=14, id=14, status='pass'), new_run)
        assert new_run.status == 'finished pass'

    def test_run_status_one_dead(self):
        run_name = "run_status_one_dead"
        new_run = Run(run_name)
        Job(dict(job_id=15, id=15, status='dead'), new_run)
        Job(dict(job_id=50, id=50, status='pass'), new_run)
        assert new_run.status == 'finished fail'

    def test_run_status_all_dead(self):
        run_name = "run_status_all_dead"
        new_run = Run(run_name)
        Job(dict(job_id=16, id=16, status='dead'), new_run)
        #Job(dict(job_id=16, id=16, status='dead'), new_run)
        assert new_run.status == 'finished dead'

    def test_run_user(self):
        run_name = "teuthology-2013-12-22_01:00:02-x-x-x-x-x"
        new_run = Run(run_name)
        assert new_run.user == "teuthology"

    def test_run_machine_type(self):
        run_name = "x-2013-12-22_01:00:02-big-x-x-x-plana"
        new_run = Run(run_name)
        assert new_run.machine_type == "plana"

    def test_run_results(self):
        run_name = 'teuthology-2014-03-27_00:00:00-x-x-x-x-x'
        new_run = Run(run_name)
        stats_in = {'pass': 9, 'fail': 1, 'dead': 6, 'running': 5, 'sha1': None,
                    'waiting': 1, 'unknown': 1, 'queued': 1}
        statuses = stats_in.keys()
        stats_in['total'] = sum(_ for _ in stats_in.values() if _)
        stats_out = {}
        for i in range(stats_in['total']):
            for status in statuses:
                count = stats_out.get(status, 0)
                count += 1
                # treat None as 0
                if count <= (stats_in[status] or 0):
                    break
            Job(dict(job_id=70+i, id=int(70+i) ,status=status), new_run)
            stats_out[status] = count
        assert new_run.get_results() == stats_in
