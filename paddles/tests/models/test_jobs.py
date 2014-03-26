from paddles.models import Job, Run, Node
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
