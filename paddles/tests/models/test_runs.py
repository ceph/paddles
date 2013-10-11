from paddles.models import Job, Run
from paddles.tests import TestApp
from paddles import models


class TestRunModel(TestApp):

    def test_jobs_count(self):
        Run.query.delete()
        Job.query.delete()
        new_run = Run('some-run-here')
        Job({}, new_run)
        Job({}, new_run)
        models.commit()
        run_as_json = Run.get(1).__json__()
        assert run_as_json['jobs_count'] == 2
