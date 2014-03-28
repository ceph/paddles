from pecan import abort, conf, expose, request
from paddles.controllers import error
from paddles.models import Job, Node, Session
from sqlalchemy import func
from collections import OrderedDict


class NodesController(object):
    @expose('json')
    def index(self, locked=None):
        query = Node.query
        if locked is not None:
            query = query.filter(Node.locked == locked)
        return [node.__json__() for node in query.all()]

    @expose('json')
    def job_stats(self, machine_type=''):
        def build_query(status=None, machine_type=None):
            query = Session.query(Node, func.count(Job.id).label('total'))
            if machine_type:
                if machine_type not in Node.machine_types:
                    abort(400)
                query = query.filter(Node.machine_type == machine_type)
            if status:
                query = query.filter(Job.status == status)
            query = query.join(Job.target_nodes)\
                .group_by(Node).order_by('total DESC')
            return query

        all_stats = dict()
        for status in Job.allowed_statuses:
            query = build_query(status, machine_type)
            results = query.all()
            for item in results:
                node = item[0]
                node_stats = all_stats.get(node.name, dict())
                node_stats[status] = item[1]
                if node_stats:
                    all_stats[node.name] = node_stats

        stats_sorter = lambda t: t[1].get('dead', 0) + t[1].get('fail', 0)
        ordered_stats = OrderedDict(sorted(all_stats.items(),
                                           key=stats_sorter))
        return ordered_stats

    @expose('json')
    def _lookup(self, name, *remainder):
        return NodeController(name), remainder


class NodeController(object):
    def __init__(self, name):
        self.name = name
        try:
            self.node = Node.query.filter_by(name=name).first()
        except ValueError:
            abort(404)
        request.context['node_name'] = self.name

    @expose(generic=True, template='json')
    def index(self):
        if not self.node:
            abort(404)
        json_node = self.node.__json__()
        return json_node

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
