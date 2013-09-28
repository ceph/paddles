from paddles.models import Job, Run
from paddles.tests import TestApp
from paddles import models


class TestJobModel(TestApp):

    def test_create_empty_job(self):
        new_run = Run('some-run-here')
        Job({}, new_run)
        models.commit()
        assert Job.get(1)

