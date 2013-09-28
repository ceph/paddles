from paddles.models import Job
from paddles.tests import TestApp
from paddles import models


class TestJobModel(TestApp):

    def test_create_empty_job(self):
        Job({})
        models.commit()
        assert Job.get(1)

