from paddles.models import Job, Run
from paddles.tests import TestApp
from paddles import models


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
