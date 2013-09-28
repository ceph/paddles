from pecan import expose, abort, request
from paddles.models import Job
from paddles.controllers import error


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

    @index.when(method='PUT', template='json')
    def index_post(self):
        """
        We update a job here, it should obviously exist already but most likely
        the data is empty.
        """
        if not self.job:
            error(
                '/errors/not_found/',
                'attempted to update a non-existent job'
            )
        self.job.update(request.json)
        return dict()
