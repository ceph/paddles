import logging
from sqlalchemy.orm import load_only

from pecan import expose, abort, request

from paddles import models
from paddles.models import Job, rollback
from paddles.controllers import error

log = logging.getLogger(__name__)


class JobController(object):

    def __init__(self, job_id):
        self.job_id = int(job_id)
        run_name = request.context.get('run_name')
        if not run_name:
            self.run = None
        else:
            run_q = models.Run.query.filter(
                models.Run.name == run_name)
            if run_q.count() == 1:
                self.run = run_q.one()
            elif run_q.count() > 1:
                error('/errors/invalid/', 'there are %s runs with that name!' %
                      run_q.count())
            else:
                self.run = None

        query = Job.query.options(load_only('id', 'job_id', 'name', 'status'))
        query = query.filter_by(job_id=job_id, run=self.run)
        self.job = query.first()

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
        old_job_status = self.job.status
        self.job.update(request.json)
        if self.job.status != old_job_status:
            log.info("Job %s/%s status changed from %s to %s", self.job.name,
                     self.job.job_id, old_job_status, self.job.status)
        return dict()

    @index.when(method='DELETE', template='json')
    def index_delete(self):
        if not self.job:
            error('/errors/not_found/',
                  'attempted to delete a non-existent job')
        log.info("Deleting job %r", self.job)
        run = self.job.run
        self.job.delete()
        run.set_status()
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
            log.info("Creating run: %s", run_name)
            run = models.Run(run_name)
            return run

    @expose(generic=True, template='json')
    def index(self, status='', fields=''):
        job_query = Job.filter_by(run=self.run)
        if status:
            job_query = job_query.filter_by(status=status)
        jobs = job_query.order_by(Job.posted.desc()).all()
        if fields:
            try:
                return [job.slice(fields) for job in jobs]
            except AttributeError:
                rollback()
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
        except ValueError:
            rollback()
            error('/errors/invalid/', 'could not decode JSON body')

        if 'job_id' in data:
            job_id = data['job_id']
            if isinstance(job_id, basestring):
                data['job_id'] = job_id = int(job_id)

            query = Job.query.options(load_only('id', 'job_id'))
            query = query.filter_by(job_id=job_id, run=self.run)
            if query.first():
                error('/errors/invalid/',
                      "job with job_id %s already exists" % job_id)

        self.job = Job(data, self.run)
        job_id = self.job.job_id
        log.info("Created job: %s/%s", data.get('name', '<no name!>'), job_id)
        return dict(job_id=job_id)

    @expose('json')
    def _lookup(self, job_id, *remainder):
        return JobController(job_id), remainder
