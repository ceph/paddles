from paddles.models import Job, Run
from paddles.tests import TestApp
from paddles import models
from datetime import datetime


class TestJobModel(TestApp):

    def test_basic_creation(self):
        new_run = Run('some-run-here')
        Job({}, new_run)
        models.commit()
        assert Job.get(1)

    def test_basic_deletion(self):
        new_run = Run('some-run-here')
        new_job = Job({'job_id': '42'}, new_run)
        models.commit()
        new_job.delete()
        models.commit()
        assert not Job.filter_by(job_id='42').first()

    def test_relationship_works(self):
        new_run = Run('some-run-here')
        Job({}, new_run)
        models.commit()
        new_job = Job.get(1)
        assert new_job.run.name == 'some-run-here'

    def test_job_updated(self):
        new_run = Run('test_job_updated')
        Job({}, new_run)
        models.commit()
        new_job = Job.get(1)
        assert isinstance(new_job.updated, datetime)
