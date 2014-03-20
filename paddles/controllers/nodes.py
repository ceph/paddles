from pecan import abort, conf, expose, request
from paddles.controllers import error
from paddles.models import Job, Node


class NodesController(object):
    @expose('json')
    def index(self):
        return [node.name for node in Node.query.all()]

    @expose('json')
    def _lookup(self, name, *remainder):
        return NodeController(name), remainder


class NodeController(object):
    def __init__(self, name):
        self.name = name
        try:
            self.node = Node.query.filter_by(name=name).first()
        except ValueError:
            self.node = None
        request.context['node_name'] = self.name

    @expose(generic=True, template='json')
    def index(self):
        if not self.node:
            abort(404)
        json_node = self.node.__json__()
        return json_node

    @expose('json')
    def jobs(self, name='', count=0):
        jobs = Job.query.filter(Job.target_nodes.contains(self.node))
        if name:
            jobs = jobs.filter(Job.name == name)
        if count:
            jobs = jobs.limit(count)
        return [job.__json__() for job in jobs]
