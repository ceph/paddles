from paddles.models import Job, Run
from paddles.tests import TestApp
from paddles import models


class TestJobModel(TestApp):

    def test_basic_creation(self):
        new_run = Run('some-run-here')
        Job({}, new_run)
        models.commit()
        assert Job.get(1)

    def test_relationship_works(self):
        new_run = Run('some-run-here')
        Job({}, new_run)
        models.commit()
        new_job = Job.get(1)
        assert new_job.run.name == 'some-run-here'
