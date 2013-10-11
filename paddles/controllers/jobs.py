from pecan import expose, abort, request
from paddles.models import Job
from paddles.controllers import error


class JobController(object):

    def __init__(self, job_id):
        self.job_id = str(job_id)
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


class JobsController(object):

    @property
    def run(self):
        run = request.context.get('run')
        if not run:
            error('/errors/notfound', 'associated run was not found')
        return run

    @expose(generic=True, template='json')
    def index(self):
        return Job.filter_by(
            run=self.run).order_by(Job.timestamp.desc()).limit(10).all()

    @index.when(method='POST', template='json')
    def index_post(self):
        """
        We create new jobs associated to this run here
        """
        try:
            data = request.json
            job_id = data.get('job_id')
        except ValueError:
            error('/errors/invalid/', 'could not decode JSON body')
        # we allow empty data to be pushed
        if not job_id:
            error('/errors/invalid/', "could not find required key: 'job_id'")
        # Make sure this doesn't exist already
        job_id = str(job_id)
        if not Job.filter_by(job_id=job_id, run=self.run).first():
            new_job = Job(data, self.run)
            return dict()
        else:
            error('/errors/invalid/', "job with job_id %s already exists" % job_id)

    @expose('json')
    def _lookup(self, job_id, *remainder):
        return JobController(job_id), remainder
