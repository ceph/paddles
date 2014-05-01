from pecan import abort, expose, request
from paddles.controllers import error
from paddles.models import Job, Node, Session, rollback
from sqlalchemy import func
from sqlalchemy.orm import aliased, load_only
from collections import OrderedDict
from datetime import datetime, timedelta


class NodesController(object):
    @expose(generic=True, template='json')
    def index(self, locked=None, machine_type='', locked_by=None):
        query = Node.query
        if locked is not None:
            query = query.filter(Node.locked == locked)
        if machine_type:
            if '|' in machine_type:
                machine_types = machine_type.split('|')
                query = query.filter(Node.machine_type.in_(machine_types))
            else:
                query = query.filter(Node.machine_type == machine_type)
        if locked_by:
            query = query.filter(Node.locked_by == locked_by)
        return [node.__json__() for node in query.all()]

    @index.when(method='POST', template='json')
    def index_post(self):
        """
        Create a new node
        """
        try:
            data = request.json
            name = data.get('name')
        except ValueError:
            rollback()
            error('/errors/invalid/', 'could not decode JSON body')
        # we allow empty data to be pushed
        if not name:
            error('/errors/invalid/', "could not find required key: 'name'")

        if Node.filter_by(name=name).first():
            error('/errors/invalid/',
                  "Node with name %s already exists" % name)
        else:
            self.node = Node(name=name)
            self.node.update(data)
        return dict()

    @expose('json')
    def job_stats(self, machine_type='', since_days=14):
        since_days = int(since_days)
        if since_days < 1:
            error('/errors/invalid/', "since_days must be a positive integer")

        now = datetime.utcnow()
        past = now - timedelta(days=since_days)
        recent_jobs = Job.query.filter(Job.posted.between(past,
                                                          now)).subquery()
        RecentJob = aliased(Job, recent_jobs)

        query = Session.query(Node.name,
                              RecentJob.status,
                              func.count('*'))

        if machine_type:
            # Note: filtering by Job.machine_type (as below) greatly improves
            # performance but could lead slightly incorrect values if many jobs
            # are being scheduled using mixed machine types. We work around
            # this by including the 'multi' machine type (which is the name of
            # the queue Inktank uses for such jobs.
            query = query.filter(RecentJob.machine_type.in_((machine_type,
                                                             'multi')))
            query = query.filter(Node.machine_type == machine_type)

        query = query.join(RecentJob.target_nodes).group_by(Node)\
            .group_by(RecentJob.status)

        all_stats = {}
        results = query.all()
        for (name, status, count) in results:
            node_stats = all_stats.get(name, {})
            node_stats[status] = count
            all_stats[name] = node_stats

        stats_sorter = lambda t: sum(t[1].values())
        ordered_stats = OrderedDict(sorted(all_stats.items(),
                                           key=stats_sorter))
        return ordered_stats

    @expose('json')
    def _lookup(self, name, *remainder):
        return NodeController(name), remainder


class NodeController(object):
    def __init__(self, name):
        self.name = name
        node_q = Node.query.options(load_only('id', 'name'))\
            .filter(Node.name == name)
        self.node = node_q.first()
        request.context['node_name'] = self.name

    @expose(generic=True, template='json')
    def index(self):
        if not self.node:
            abort(404)
        json_node = self.node.__json__()
        return json_node

    @index.when(method='PUT', template='json')
    def index_put(self):
        """
        Update the Node object here
        """
        if not self.node:
            error(
                '/errors/not_found/',
                'attempted to update a non-existent node'
            )
        self.node.update(request.json)
        return dict()

    @expose(generic=True, template='json')
    def lock(self):
        error(
            '/errors/invalid/',
            'this URL only makes sense as a PUT request'
            )

    @lock.when(method='PUT', template='json')
    def lock_put(self):
        node_dict = request.json
        if not self.node:
            error(
                '/errors/not_found/',
                'attempted to lock a non-existent node'
            )
        elif self.node.locked and node_dict.get('locked', False) is True:
            error(
                '/errors/forbidden/',
                'attempted to lock a locked node'
            )
        self.node.update(node_dict)
        return self.node.__json__()

    @expose('json')
    def jobs(self, name='', status='', count=0):
        if not self.node:
            abort(404)
        jobs = Job.query.filter(Job.target_nodes.contains(self.node))
        if name:
            jobs = jobs.filter(Job.name == name)
        if status:
            jobs = jobs.filter(Job.status == status)
        if count:
            jobs = jobs.limit(count)
        return [job.__json__() for job in jobs]

    @expose('json')
    def job_stats(self):
        if not self.node:
            abort(404)
        all_jobs = Job.query.filter(Job.target_nodes.contains(self.node))
        stats = dict()
        for status in Job.allowed_statuses:
            stats[status] = all_jobs.filter(Job.status == status).count()
        return stats
