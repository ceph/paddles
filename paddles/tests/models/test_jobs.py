from paddles.models import Job, Run, Node
from paddles.util import local_datetime_to_utc
from paddles.tests import TestApp
from paddles import models
from datetime import datetime

import pytest


class TestJobModel(TestApp):

    def test_basic_creation(self):
        new_run = Run('test_basic_creation')
        Job({}, new_run)
        models.commit()
        assert Job.get(1)

    def test_basic_deletion(self):
        new_run = Run('test_basic_deletion')
        new_job = Job({'job_id': '42'}, new_run)
        models.commit()
        new_job.delete()
        models.commit()
        assert not Job.filter_by(job_id='42').first()

    def test_relationship_works(self):
        new_run = Run('test_relationship_works')
        id_ = Job({}, new_run).id
        models.commit()
        new_job = Job.get(id_)
        assert new_job.run.name == 'test_relationship_works'

    def test_job_updated(self):
        new_run = Run('test_job_updated')
        Job({}, new_run)
        models.commit()
        new_job = Job.get(1)
        assert isinstance(new_job.updated, datetime)

    def test_job_slice_valid(self):
        run_name = 'test_job_slice_valid'
        new_run = Run(run_name)
        new_job = Job({'description': 'describe the test'}, new_run)
        assert 'description' in new_job.slice('description')

    def test_job_slice_valid_many(self):
        run_name = 'test_job_slice_valid_many'
        new_run = Run(run_name)
        new_job = Job({'job_id': '9', 'description': 'describe the test'},
                      new_run)
        job_slice = new_job.slice('description,job_id,href')
        assert ('description' in job_slice and 'job_id' in job_slice and 'href'
                in job_slice)

    def test_job_slice_invalid(self):
        run_name = 'test_job_slice_invalid'
        new_run = Run(run_name)
        new_job = Job({}, new_run)
        with pytest.raises(AttributeError):
            new_job.slice('bullcrap')

    def test_job_creates_node(self):
        run_name = 'test_job_creates_node'
        node_name = 'node.name'
        targets = {'foo@' + node_name: ''}
        new_run = Run(run_name)
        Job(dict(targets=targets), new_run)
        assert Node.get(1).name == node_name

    def test_job_creates_many_nodes(self):
        run_name = 'test_job_creates_many_nodes'
        node_names = ['node1.name', 'node2.name', 'node3.name']
        targets = {}
        for name in node_names:
            targets['foo@' + name] = ''
        new_run = Run(run_name)
        Job(dict(targets=targets), new_run)
        assert sorted([node.name for node in Node.query.all()]) == node_names

    def test_force_updated_time(self):
        run_name = 'test_force_updated_time'
        run = Run(run_name)
        time_stamp = '2014-03-31 21:25:43'
        Job(dict(updated=time_stamp), run)
        models.commit()
        local_dt = datetime.strptime(time_stamp, '%Y-%m-%d %H:%M:%S')
        utc_dt = local_datetime_to_utc(local_dt)
        job = Run.query.filter(Run.name == run.name).one().jobs[0]
        assert str(job.updated) == str(utc_dt)

    def test_success_updates_status(self):
        run_name = 'test_success_updates_status'
        run = Run(run_name)
        job_id = '27'
        job = Job(dict(name=run_name, job_id=job_id, status='running'), run)
        print job.status, job.success
        models.commit()
        job.update(dict(success=True))
        print job.status, job.success
        models.commit()
        assert job.status == 'pass'

    def test_status_dead_ignored_when_success_set(self):
        run_name = 'test_status_dead_ignored_when_success_set'
        run = Run(run_name)
        job_id = '27'
        job = Job(dict(name=run_name, job_id=job_id, status='running'), run)
        models.commit()
        job.update(dict(success=True))
        models.commit()
        job.update(dict(status='dead'))
        models.commit()
        assert job.status == 'pass'
