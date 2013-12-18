from pecan import expose, abort, request
from paddles import models
from paddles.models import Job
from paddles.controllers import error


class JobController(object):

    def __init__(self, job_id):
        self.job_id = str(job_id)
        run_name = request.context.get('run_name')
        if not run_name:
            self.run = None
        else:
            run_q = models.Run.query.filter(
                models.Run.name == run_name)
            if run_q.count() == 1:
                self.run = run_q.one()
            elif run_q.count() > 1:
                error('/errors/invalid/',
                    'there are %s runs with that name!' % run_q.count())
            else:
                self.run = None
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

    @index.when(method='DELETE', template='json')
    def index_delete(self):
        if not self.job:
            error('/errors/not_found/',
                  'attempted to delete a non-existent job')
        self.job.delete()
        return dict()


class JobsController(object):

    @property
    def run(self):
        run_name = request.context.get('run_name')
        if not run_name:
            error('/errors/notfound', 'associated run was not found and no name was provided to create one')  # noqa
        run_q = models.Run.query.filter(models.Run.name == run_name)
        if run_q.count() == 1:
            run = run_q.one()
            return run
        elif run_q.count() > 1:
            error('/errors/invalid/',
                  'there are %s runs with that name!' % run_q.count())
        elif run_q.count() == 0:
            run = models.Run(run_name)
            return run

    @expose(generic=True, template='json')
    def index(self, fields=''):
        jobs = Job.filter_by(
            run=self.run).order_by(Job.posted.desc()).all()
        if fields:
            try:
                return [job.slice(fields) for job in jobs]
            except AttributeError:
                error('/errors/invalid/',
                      'an invalid field was specified')
        else:
            return jobs

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
        job_id = data['job_id'] = str(job_id)

        if Job.filter_by(job_id=job_id, run=self.run).first():
            error('/errors/invalid/',
                  "job with job_id %s already exists" % job_id)
        self.job = Job(data, self.run)
        return dict()

    @expose('json')
    def _lookup(self, job_id, *remainder):
        return JobController(job_id), remainder
