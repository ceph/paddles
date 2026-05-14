import logging

import psycopg.errors
from pecan import abort, expose, request
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only

from paddles import models
from paddles.controllers import create_run, date_from_string, error
from paddles.controllers.util import offset_query
from paddles.decorators import retryOperation

from ..models import Job, Session, rollback

log = logging.getLogger(__name__)


class JobController(object):
    def __init__(self, job_id):
        self.job_id = str(job_id)
        run_name = request.context.get("run_name")
        if not run_name:
            self.run = None
        else:
            run_count = Session.scalar(
                select(func.count())
                .select_from(models.Run)
                .where(models.Run.name == run_name)
            )
            if run_count == 1:
                self.run = Session.scalars(
                    select(models.Run).where(models.Run.name == run_name)
                ).one()
            elif run_count > 1:
                error(
                    "/errors/invalid/",
                    "there are %s runs with that name!" % run_count,
                )
            else:
                self.run = None

        query = select(Job).options(load_only(Job.id, Job.job_id, Job.name, Job.status))
        query = query.filter_by(job_id=job_id, run=self.run)
        self.job: Job = Session.scalars(query).first()

    @expose(generic=True, template="json")
    def index(self):
        if not self.job:
            abort(404)
        return self.job

    @index.when(method="PUT", template="json")
    @retryOperation(attempts=100)
    def index_put(self):
        """
        We update a job here, it should obviously exist already but most likely
        the data is empty.
        """
        if not self.job:
            error("/errors/not_found/", "attempted to update a non-existent job")
        old_priority = self.job.priority
        data = request.json
        if "priority" in data:
            if data["priority"] != old_priority:
                if self.job.status == "queued":
                    log.info(
                        "Job %s/%s priority changed from %s to %s",
                        self.job.name,
                        self.job.job_id,
                        old_priority,
                        data["priority"],
                    )
                else:
                    log.info(
                        "Job status %s. Priority cannot be changed", self.job.status
                    )
                    data["priority"] = old_priority
        self.job.update(data)
        Session.commit()
        log.info(f"job {self.job.job_id} COMMITTED")
        # if self.job.status != old_job_status:
        # log.info(
        #     "Job %s/%s status changed from %s to %s",
        #     self.job.name,
        #     self.job.job_id,
        #     old_job_status,
        #     self.job.status,
        # )

        return dict()

    @index.when(method="DELETE", template="json")
    def index_delete(self):
        if not self.job:
            error("/errors/not_found/", "attempted to delete a non-existent job")
        log.info("Deleting job %r", self.job)
        Session.delete(self.job)
        return dict()


class JobsController(object):
    @retryOperation
    def _find_run(self):
        self.run_name = run_name = request.context.get("run_name")
        run_count = Session.scalar(
            select(func.count())
            .select_from(models.Run)
            .where(models.Run.name == run_name)
        )
        if run_count > 0:
            return Session.scalars(
                select(models.Run).where(models.Run.name == run_name)
            ).one()
        else:
            return None

    def _create_run(self):
        self.run = run = create_run(self.run_name)
        return run

    @expose(generic=True, template="json")
    def index(self, status="", fields=""):
        self.run = self._find_run()
        if not self.run:
            error("/errors/notfound", "associated run was not found")
        job_query = select(Job).filter_by(run=self.run)
        if status:
            job_query = job_query.filter_by(status=status)
        jobs = Session.scalars(job_query.order_by(Job.posted.desc())).all()
        if fields:
            try:
                return [job.slice(fields) for job in jobs]
            except AttributeError:
                rollback()
                error("/errors/invalid/", "an invalid field was specified")
        else:
            return jobs

    @index.when(method="POST", template="json")
    def index_post(self):
        """
        We create new jobs associated to this run here
        """
        try:
            data = request.json
            if not data:
                raise ValueError()
        except ValueError:
            rollback()
            error("/errors/invalid/", "could not decode JSON body")
        # we allow empty data to be pushed
        self.run = self._find_run()
        if not self.run:
            self._create_run()

        job = self._create_job(data)
        # try:
        #     job = self._create_job(data)
        # except Exception as e:
        #     error("/errors/unavailable/", str(e))
        return dict({"job_id": job.job_id, "status": job.status})

    @retryOperation
    def _create_job(self, data):
        if "job_id" in data:
            if "queue" in data:
                error("/errors/invalid/", "job cannot contain both job_id and queue")
            job_id = str(data["job_id"])
            try:
                with Session.no_autoflush:
                    self.job = Job(data, self.run)
                Session.add(self.job)
                models.commit()
                log.info("Created job: %s/%s", data.get("name", "<no name!>"), job_id)
                return self.job
            except IntegrityError as e:
                Session.rollback()
                if isinstance(
                    e.orig, psycopg.errors.UniqueViolation
                ):
                    # log.info(f"tried to create job {job_id} but it exists already")
                    error(
                        "/errors/invalid/", f"job with job_id {job_id} already exists"
                    )
                else:
                    log.exception("failed to create job")
                # FIXME: is the below what we should be doing?
                query = select(Job).where(
                    Job.job_id == job_id, Job.run.has(name=self.run_name)
                )
                self.job = Session.scalars(query).one()
                return self.job

            query = select(Job).where(
                Job.job_id == job_id, Job.run.has(name=self.run_name)
            )
            query = query.options(load_only(Job.id, Job.job_id))
            if Session.scalars(query).first():
                error("/errors/invalid/", "job with job_id %s already exists" % job_id)
            else:
                log.info("Creating job: %s/%s", data.get("name", "<no name!>"), job_id)
                self.job = Job(data, self.run)
                Session.add(self.job)
                try:
                    models.commit()
                except Exception as e:
                    log.error(
                        f"failed to create job {job_id=} name={data['name']} {str(e).split()[0]}"
                    )
                    models.rollback()
                    log.error(f"q={Session.scalars(query).first()}")
                    # raise
                    error("/errors/invalid", str(e.args[0]))
                return self.job
        else:
            if "queue" not in data:
                error("/errors/invalid/", "job must contain either job_id or queue")
            # with paddles as queue backend, we generate job ID here
            with Session.no_autoflush:
                self.job = Job(data, self.run)
            Session.add(self.job)
            # Generate job_id based on existing jobs in the run
            # With lazy='select', self.run.jobs is a regular list
            existing_job_ids = [
                int(job.job_id) for job in self.run.jobs
                if job.job_id is not None and job.job_id.isdigit()
            ]
            self.job.job_id = str(max(existing_job_ids or [0]) + 1)
            try:
                Session.commit()
            except Exception as e:
                log.error(f"failed to create job {str(e)=}")
                error("/errors/invalid", str(e.args[0]))
            log.info("Job ID of created job is %s", self.job.job_id)
            return self.job

    @expose("json")
    def _lookup(self, job_id, *remainder):
        return JobController(job_id), remainder


class JobsListController(object):
    @expose("json")
    def index(
        self,
        description="",
        status="",
        sha1="",
        branch="",
        user="",
        posted_after="",
        posted_before="",
        count=10,
        page=1,
    ):
        """
        List latest jobs.
        Filter by sha1, branch, username, posted date (range:- posted_before:posted_after), description, and status.
        """
        job_query = select(Job).order_by(desc(Job.posted))

        if description:
            job_query = job_query.filter(Job.description.contains(description))

        if status:
            job_query = job_query.filter_by(status=status)

        if sha1:
            job_query = job_query.filter_by(sha1=sha1)
        elif branch:
            job_query = job_query.filter_by(branch=branch)

        if user:
            job_query = job_query.filter_by(user=user)

        if posted_after:
            posted_after = date_from_string(posted_after)[1]
            job_query = job_query.filter(Job.posted > posted_after)

        if posted_before:
            posted_before = date_from_string(posted_before)[1]
            job_query = job_query.filter(Job.posted < posted_before)

        job_query = offset_query(job_query, page_size=count, page=page)
        jobs = Session.scalars(job_query).all()

        return jobs
