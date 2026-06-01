import logging

from pecan import expose, request
from sqlalchemy import select

from paddles.controllers import error
from paddles.exceptions import PaddlesError
from paddles.models import Job, Queue, Run

log = logging.getLogger(__name__)


class QueuesController(object):
    @expose(generic=True, template="json")
    def index(self, machine_type="", paused_by=None):
        query = select(Queue)
        if machine_type:
            if "|" in machine_type:
                query = query.filter(Queue.queue == "multi")
            else:
                query = query.filter(Queue.queue == machine_type)
        if paused_by:
            query = query.filter(Queue.paused_by == paused_by)
        return [queue.__json__() for queue in request.session.scalars(query).all()]

    @index.when(method="POST", template="json")
    def index_post(self):
        """
        Create a new Queue
        """
        session = request.session
        try:
            data = request.json
            queue_name = data.get("queue")
        except ValueError:
            error("/errors/invalid/", "could not decode JSON body")
        if not queue_name:
            error("/errors/invalid/", "could not find required key: 'queue'")

        if session.scalars(select(Queue).filter_by(queue=queue_name)).first():
            error("/errors/invalid/", "Queue %s already exists" % queue_name)
        else:
            self.queue = Queue(queue=queue_name)
            try:
                self.queue.update(data)
            except PaddlesError as exc:
                error(exc.url, str(exc))
            session.add(self.queue)
            log.info(
                "Created {queue}: {data}".format(
                    queue=self.queue,
                    data=data,
                )
            )
        return dict()

    @index.when(method="PUT", template="json")
    def index_put(self):
        """
        Update the Queue
        """
        try:
            data = request.json
            queue_name = data.get("queue")
        except ValueError:
            error("/errors/invalid/", "could not decode JSON body")
        if not queue_name:
            error("/errors/invalid/", "could not find required key: 'queue'")
        queue = request.session.scalars(select(Queue).filter_by(queue=queue_name)).first()
        if queue:
            self.queue = queue
            try:
                self.queue.update(data)
            except PaddlesError as exc:
                error(exc.url, str(exc))
            log.info(
                "Updated {queue}: {data}".format(
                    queue=self.queue,
                    data=data,
                )
            )
        else:
            error("/errors/invalid/", "specified queue does not exist")
        return dict()

    @expose(template="json")
    def pop_queue(self, queue):
        session = request.session
        queue_name = queue
        queue = session.scalars(select(Queue).filter_by(queue=queue_name)).first()
        if queue is None:
            log.info("%s queue is empty! No jobs to retrieve", queue_name)
            return None
        if queue.paused is True:
            error("/errors/unavailable/", "queue is paused, cannot retrieve job")
            return
        job_query = select(Job).filter_by(status="queued").filter_by(queue=queue_name)
        job = session.scalars(job_query.order_by(Job.priority)).first()
        return job

    @expose(template="json")
    def stats(self, queue):
        session = request.session
        queue_name = queue
        if not queue_name:
            error("/errors/invalid/", "could not find required key: 'queue'")
        queue = session.scalars(select(Queue).filter_by(queue=queue_name)).first()
        if queue:
            stats = session.scalars(
                select(Job).filter_by(queue=queue_name).filter_by(status="queued")
            ).all()
            current_jobs_ready = len(stats)

            if queue.__json__()["paused"] is False:
                return dict(
                    queue=queue_name,
                    queued_jobs=current_jobs_ready,
                    paused=queue.__json__()["paused"],
                )
            else:
                paused_stats = queue.__json__()
                paused_stats.update(queued_jobs=current_jobs_ready)
                return paused_stats
        else:
            error("/errors/invalid/", "specified queue does not exist")

    @expose(template="json")
    def queued_jobs(self, queue, user=None, run_name=None):
        """
        Retrieve all the queued jobs for a particular user or a particular run
        """
        session = request.session
        queue_name = queue
        if not queue_name:
            error("/errors/invalid/", "could not find required key: 'queue'")
        queue = session.scalars(select(Queue).filter_by(queue=queue_name)).first()
        if not queue:
            error("/errors/invalid/", "specified queue does not exist")
        else:
            jobs_query = select(Job).where(Job.status == "queued").where(Job.queue == queue_name)
            if run_name:
                jobs_query = jobs_query.where(Run.name == run_name).where(Run.id == Job.run_id)
            elif user:
                jobs_query = jobs_query.where(Job.user == user)
            return [job.__json__() for job in session.scalars(jobs_query).all()]
