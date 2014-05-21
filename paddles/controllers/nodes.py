from pecan import abort, expose, request
from paddles.controllers import error
from paddles.models import Job, Node, Session, rollback
from sqlalchemy import func
from sqlalchemy.orm import aliased, load_only
from collections import OrderedDict
from datetime import datetime, timedelta

import logging
log = logging.getLogger(__name__)


class NodesController(object):
    @expose(generic=True, template='json')
    def index(self, locked=None, machine_type='', locked_by=None, up=None):
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
        if up is not None:
            query = query.filter(Node.up == up)
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

    @expose(generic=True, template='json')
    def lock_many(self):
        error('/errors/invalid/',
              "this URI only supports POST requests")

    @lock_many.when(method='POST', template='json')
    def lock_many_post(self):
        req = request.json
        fields = ['count', 'locked_by', 'machine_type', 'description']
        if sorted(req.keys()) != sorted(fields):
            error('/errors/invalid/',
                  "must pass these fields: %s" % ', '.join(fields))

        req['locked'] = True

        count = req.pop('count', 0)
        if count < 1:
            error('/errors/invalid/',
                  "cannot lock less than 1 node")

        machine_type = req.pop('machine_type', None)
        if not machine_type:
            error('/errors/invalid/',
                  "must specify machine_type")

        query = Node.query
        query = query.filter(Node.machine_type == machine_type)
        query = query.filter(Node.up.is_(True))

        # First, try to recycle a user's already-locked nodes if description
        # matches. In this case we don't care if the nodes are locked or not.
        locked_by = req.get('locked_by')
        description = req.get('description')
        if description is not None:
            recycle_q = query.filter(Node.locked_by == locked_by)
            recycle_q = recycle_q.filter(Node.description == description)
            recycle_q = recycle_q.limit(count)
            nodes = recycle_q.all()
            nodes_avail = len(nodes)
            if nodes_avail == count:
                log.info("Re-using {count} locks for {locked_by}".format(
                    count=count, locked_by=locked_by))
                return nodes

        # Find unlocked nodes
        query = query.filter(Node.locked.is_(False))
        query = query.limit(count)
        nodes = query.all()
        nodes_avail = len(nodes)
        if nodes_avail < count:
            error('/errors/unavailable/',
                  "only {count} nodes available".format(count=nodes_avail))

        for node in nodes:
            log.info("Locking {count} nodes for {locked_by}".format(
                count=count, locked_by=locked_by))
            node.update(req)

        return [node for node in nodes]

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
            error(
                '/errors/not_found/',
                'node not found'
            )
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
        update = request.json
        log.info("Updating {node}: {data}".format(
            node=self.node,
            data=update,
        ))
        self.node.update(update)
        return dict()

    @expose(generic=True, template='json')
    def lock(self):
        if request.method == 'PUT':
            node_dict = request.json
        else:
            node_dict = dict()
        verb_dict = {False: 'unlock', True: 'lock', None: 'check'}
        verb = verb_dict[node_dict.get('locked')]
        owner = node_dict.get('locked_by')

        if not self.node:
            error(
                '/errors/not_found/',
                'attempted to {verb} a non-existent node'.format(
                    verb=verb
                )
            )
        elif 'lock' in verb and not owner:
            error(
                '/errors/invalid',
                'cannot {verb} without specifying locked_by'.format(
                    verb=verb)
            )
        elif self.node.locked and verb == 'lock':
            error(
                '/errors/forbidden/',
                'attempted to lock a locked node'
            )
        elif 'lock' in verb and self.node.locked and \
                owner != self.node.locked_by:
            error(
                '/errors/forbidden/',
                'cannot {verb} - owners do not match'.format(
                    verb=verb
                )
            )

        if request.method == 'PUT':
            if 'lock' in verb:
                word = dict(lock='Locking', unlock='Unlocking')[verb]
            log.info("{word} {node} for {owner}".format(
                word=word, node=self.node, owner=owner))
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
