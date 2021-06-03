from pecan import expose, request
from paddles.controllers import error
from paddles.exceptions import PaddlesError
from paddles.models import Queue, Job, Session

import logging
log = logging.getLogger(__name__)

class QueuesController(object):
    @expose(generic=True, template='json')
    def index(self, paused=None, machine_type='', paused_by=None):
        query = Queue.query
        if paused is not None:
            query = query.filter(Queue.paused == paused)
        if machine_type:
            if '|' in machine_type:
                machine_types = machine_type.split('|')
                query = query.filter(Queue.machine_type.in_(machine_types))
            else:
                query = query.filter(Queue.machine_type == machine_type)
        if paused_by:
            query = query.filter(Queue.paused_by == paused_by)
        return [queue.__json__() for queue in query.all()]
    
    @index.when(method='POST', template='json')
    def index_post(self):
        """
        Create a new Queue
        """
        try:
            data = request.json
            machine_type = data.get('machine_type')
        except ValueError:
            error('/errors/invalid/', 'could not decode JSON body')
        if not machine_type:
            error('/errors/invalid/', "could not find required key: 'machine_type'")

        if Queue.filter_by(machine_type=machine_type).first():
            error('/errors/invalid/',
                  "Queue for machine type %s already exists" % machine_type)
        else:
            self.queue = Queue(machine_type=machine_type)
            try:
                self.queue.update(data)
            except PaddlesError as exc:
                error(exc.url, str(exc))
            log.info("Created {queue}: {data}".format(
                queue=self.queue,
                data=data,
            ))
        return dict()

    @index.when(method='PUT', template='json')
    def index_put(self):
        """
        Update the Queue
        """
        try:
            data = request.json
            machine_type = data.get('machine_type')
        except ValueError:
            error('/errors/invalid', 'could not decode JSON body')
        if not machine_type:
            error('/errors/invalid/', "could not find required key: 'machine_type'")
        queue = Queue.filter_by(machine_type=machine_type).first()
        if queue:
            self.queue = queue
            try:
                self.queue.update(data)
            except PaddlesError as exc:
                error(exc.url, str(exc))
            log.info("Updated {queue}: {data}".format(
                queue=self.queue,
                data=data,
            ))
        else:
            error('/errors/invalid', "queue for specified 'machine_type' does not exist")
        return dict()

    @expose(template='json')
    def pop_queue(self, machine_type):
        job_query = Job.filter_by(status='queued').filter_by(machine_type=machine_type)
        job = job_query.order_by(Job.priority).first()
        return job
    
    @expose(template='json')
    def stats(self):
        try:
            data = request.json
            machine_type = data.get('machine_type')
        except ValueError:
            error('/errors/invalid', 'could not decode JSON body')
        if not machine_type:
            error('/errors/invalid/', "could not find required key: 'machine_type'")
        queue = Queue.filter_by(machine_type=machine_type).first()
        if queue:
            stats = Session.query(Queue, Job).\
                filter(Queue.machine_type == Job.machine_type).\
                filter(Job.status=='queued').\
                filter(Queue.machine_type==machine_type).\
                all()
            current_jobs_ready = len(stats)
            pause_duration = Session.query(Queue.pause_duration).filter(Queue.machine_type==machine_type).first()[0]
            return dict(
                name=machine_type,
                count=current_jobs_ready,
                paused=pause_duration,
            )
        else:
            error('/errors/invalid', "queue for specified 'machine_type' does not exist")


    @expose(template='json')
    def queued_jobs(self):
        """
        Retrieve all the queued jobs for a particular user
        """
        try:
            data = request.json
            machine_type = data.get('machine_type')
            user = data.get('user')
        except ValueError:
            error('/errors/invalid', 'could not decode JSON body')
        if not machine_type:
            error('/errors/invalid/', "could not find required key: 'machine_type'")
        if not user:
            error('/errors/invalid/', "could not find required key: 'user'")
        queue = Queue.filter_by(machine_type=machine_type).first()
        if queue:
            jobs = Session.query(Job).\
                filter(Queue.machine_type==Job.machine_type).\
                filter(Queue.machine_type==machine_type).\
                filter(Job.status=='queued').\
                filter(Job.user==user)
            return [job.__json__() for job in jobs.all()]
        else:
            error('/errors/invalid', "queue for specified 'machine_type' does not exist")
