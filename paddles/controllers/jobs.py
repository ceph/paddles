from pecan import expose, abort, request
from paddles.models import Run


class JobController(object):

    def __init__(self, job_id):
        self.job_id = job_id
        try:
            self.job = Run.filter_by(job_id=job_id).first()
        except ValueError:
            self.job = None

    @expose('json')
    def index(self):
        if not self.job:
            abort(404)
        return self.job
