from paddles.models import Job, Run
from paddles.tests import TestApp
from paddles import models

import pytest


class TestRunModel(TestApp):

    def test_jobs_count(self):
        Run.query.delete()
        Job.query.delete()
        new_run = Run('test_jobs_count')
        Job({}, new_run)
        Job({}, new_run)
        models.commit()
        run_as_json = Run.get(1).__json__()
        assert run_as_json['jobs_count'] == 2

    def test_run_deletion(self):
        run_name = 'test_run_deletion'
        new_run = Run(run_name)
        Job({'job_id': '42'}, new_run)
        Job({'job_id': '120'}, new_run)
        Job({'job_id': '4'}, new_run)
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
        Job({'job_id': '42'}, new_run)
        Job({'job_id': '9999'}, new_run)
        models.commit()
        new_run.delete()
        models.commit()
        assert not Job.filter_by(job_id='9999').first()

    def test_scheduled(self):
        run_name = 'teuthology-2013-10-23_01:35:02-upgrade-small-next-testing-basic-vps'  # noqa
        new_run = Run(run_name)
        assert str(new_run.scheduled) == '2013-10-23 01:35:02'

    def test_updated(self):
        run_name = 'test_updated'
        new_run = Run(run_name)
        for i in range(1, 5):
            Job(dict(job_id=i), new_run)
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
            'teuthology-2013-10-22_03:00:02-ceph-deploy-next-testing-basic-plana'
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
            'teuthology-2013-10-22_03:00:02-ceph-deploy-wip-9999-testing-basic-plana'
        new_run = Run(run_name)
        assert (new_run.suite, new_run.branch) == ('ceph-deploy', 'wip-9999')
