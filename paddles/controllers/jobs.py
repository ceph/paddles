import logging
from sqlalchemy import Sequence
from sqlalchemy.orm import load_only

from pecan import expose, abort, request, conf

from paddles import models
from paddles.decorators import retryOperation
from paddles.models import Job, rollback, Session
from paddles.controllers import error
import paddles.controllers.runs

log = logging.getLogger(__name__)


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
    @retryOperation(attempts=100)
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
        old_priority = self.job.priority
        self.job.update(request.json)
        Session.commit()
        if self.job.status != old_job_status:
            log.info("Job %s/%s status changed from %s to %s", self.job.name,
                     self.job.job_id, old_job_status, self.job.status)
        
        if self.job.priority != old_priority:
            log.info("Job %s/%s priority changed from %s to %s", self.job.name,
                     self.job.job_id, old_priority, self.job.priority)
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
    @retryOperation
    def _find_run(self):
        self.run_name = run_name = request.context.get('run_name')
        run_q = models.Run.query.filter(models.Run.name == run_name)
        if run_q.count():
            return run_q.one()
        else:
            return None

    def _create_run(self):
        self.run = run = paddles.controllers.runs.RunsController._create_run(self.run_name)
        return run

    @expose(generic=True, template='json')
    def index(self, status='', fields=''):
        self.run = self._find_run()
        if not self.run:
            error('/errors/notfound', 'associated run was not found')
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
            if not data:
                raise ValueError()
            config = dict(conf.sqlalchemy)
            if 'sqlite' in config['url']:
                '''
                Need this check since Sequence is not supported in SQLite
                '''
                job = Session.query(Job).order_by(Job.id.desc()).first()
                if job:
                    job_id = job.id + 1
                else:
                    job_id = 1
            else:
                job_id = Session.execute(Sequence('jobs_id_seq'))
            job_id = str(job_id)
            data['job_id'] = job_id
            data['id'] = int(job_id)
        except ValueError:
            rollback()
            error('/errors/invalid/', 'could not decode JSON body')
        # we allow empty data to be pushed
        if not job_id:
            error('/errors/invalid/', "could not find required key: 'job_id'")
        self.run = self._find_run()
        if not self.run: self._create_run()

        job_id = data['job_id'] = str(job_id)

        self._create_job(job_id, data)
        return dict()

    @retryOperation
    def _create_job(self, job_id, data):
        query = Job.query.options(load_only('id', 'job_id'))
        query = query.filter_by(job_id=job_id, run=self.run)
        if query.first():
            error('/errors/invalid/',
                  "job with job_id %s already exists" % job_id)
        else:
            log.info("Job ID: %s", job_id)
            log.info("Creating job: %s/%s", data.get('name', '<no name!>'),
                     job_id)
            log.info(data)
            self.job = Job(data, self.run)
            Session.commit()
            return self.job

    @expose('json')
    def _lookup(self, job_id, *remainder):
        return JobController(job_id), remainder
