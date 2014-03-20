from pecan import abort, conf, expose, request
from paddles.controllers import error
from paddles.models import Job, Node


class NodesController(object):
    @expose('json')
    def index(self, locked=None):
        query = Node.query
        if locked is not None:
            query = query.filter(Node.locked == locked)
        return [node.name for node in query.all()]

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
