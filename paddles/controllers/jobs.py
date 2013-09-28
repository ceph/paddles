from pecan import expose, abort, request
from paddles.models import Job


class JobController(object):

    def __init__(self, job_id):
        self.job_id = job_id
        self.run = request.context['run']
        try:
            self.job = Job.filter_by(job_id=job_id, run=self.run).first()
        except ValueError:
            self.job = None

    @expose(generic=True, template='json')
    def index(self):
        if not self.job:
            abort(404)
        return self.job

    @index.when(method='POST', template='json')
    def index_post(self):
        # save to DB here
        new_job = Job(request.json)
        return dict()
