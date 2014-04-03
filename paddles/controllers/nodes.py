from pecan import abort, expose, request
from paddles.controllers import error
from paddles.models import Job, Node, Session
from sqlalchemy import func
from collections import OrderedDict


class NodesController(object):
    @expose(generic=True, template='json')
    def index(self, locked=None, machine_type=''):
        query = Node.query
        if locked is not None:
            query = query.filter(Node.locked == locked)
        if machine_type:
            query = query.filter(Node.machine_type == machine_type)
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
    def job_stats(self, machine_type=''):
        def build_query(status=None, machine_type=None):
            query = Session.query(Node, func.count(Job.id).label('total'))
            if machine_type:
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

        stats_sorter = lambda t: sum(t[1].values())
        ordered_stats = OrderedDict(sorted(all_stats.items(),
                                           key=stats_sorter))
        return ordered_stats

    @expose('json')
    def job_stats2(self, machine_type=''):
        query = Session.query(Node.name,
                              Job.status,
                              func.count('*'))\
            .join(Job.target_nodes).group_by(Node).group_by(Job.status)

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
        self.node = Node.query.filter_by(name=name).first()
        request.context['node_name'] = self.name

    @expose(generic=True, template='json')
    def index(self):
        if not self.node:
            abort(404)
        json_node = self.node.__json__()
        return json_node

    @index.when(method='PUT', template='json')
    def index_post(self):
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
