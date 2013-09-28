from pecan import expose, request
from paddles.models import Run, Job
from paddles.controllers.jobs import JobController
from paddles.controllers import error


class RunController(object):

    def __init__(self, name):
        self.name = name
        try:
            self.run = Run.filter_by(name=name).first()
        except ValueError:
            self.run = None
        request.context['run'] = self.run

    @expose(generic=True, template='json')
    def index(self):
        if not self.run:
            error('/errors/not_found/', 'requested job resource does not exist')
        return self.run

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
        if not Job.filter_by(job_id=job_id, run=self.run).first():
            new_job = Job(data, self.run)
            return dict()
        else:
            error('/errors/invalid/', "job with job_id %s already exists" % job_id)

    @expose('json')
    def _lookup(self, job_id, *remainder):
        return JobController(job_id), remainder


class RunsController(object):

    @expose(generic=True, template='json')
    def index(self):
        return Run.query.limit(10).all()

    @index.when(method='POST', template='json')
    def index_post(self):
        # save to DB here
        try:
            name = request.json.get('name')
        except ValueError:
            error('/errors/invalid/', 'could not decode JSON body')
        if not name:
            error('/errors/invalid/', "could not find required key: 'name'")
        if not Run.filter_by(name=name).first():
            new_run = Run(name)
            return dict()
        else:
            error('/errors/invalid/', "run with name %s already exists" % name)

    @expose('json')
    def _lookup(self, name, *remainder):
        return RunController(name), remainder
