from pecan import abort, expose, request
from paddles.controllers import error
from paddles.decorators import isolation_level
from paddles.exceptions import PaddlesError, RaceConditionError
from paddles.models import Job, Node, Session, rollback
from sqlalchemy import func
from sqlalchemy.orm import aliased, load_only
from collections import OrderedDict
from datetime import datetime, timedelta

import logging
log = logging.getLogger(__name__)


class NodesController(object):
    @expose(generic=True, template='json')
    def index(self, locked=None, machine_type='', os_type=None,
              os_version=None, locked_by=None, up=None, count=None):
        query = Node.query
        if locked is not None:
            query = query.filter(Node.locked == locked)
        if machine_type:
            if '|' in machine_type:
                machine_types = machine_type.split('|')
                query = query.filter(Node.machine_type.in_(machine_types))
            else:
                query = query.filter(Node.machine_type == machine_type)
        if os_type:
            query = query.filter(Node.os_type == os_type)
        if os_version:
            query = query.filter(Node.os_version == os_version)
        if locked_by:
            query = query.filter(Node.locked_by == locked_by)
        if up is not None:
            query = query.filter(Node.up == up)
        if count is not None:
            if not count.isdigit() or isinstance(count, int):
                error('/errors/invalid/', 'count must be an integer')
            query = query.limit(count)
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
            try:
                self.node.update(data)
            except PaddlesError as exc:
                error(exc.url, exc.message)
        return dict()

    @expose(generic=True, template='json')
    def lock_many(self):
        error('/errors/invalid/',
              "this URI only supports POST requests")

    @isolation_level('SERIALIZABLE')
    @lock_many.when(method='POST', template='json')
    def lock_many_post(self):
        req = request.json
        fields = set(('count', 'locked_by', 'machine_type', 'description'))
        if not fields.issubset(set(req.keys())):
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

        locked_by = req.get('locked_by')
        description = req.get('description')
        os_type = req.get('os_type')
        os_version = req.get('os_version')
        attempts = 2
        log.debug("Locking {count} {mtype} nodes for {locked_by}".format(
            count=count, mtype=machine_type, locked_by=locked_by))
        while attempts > 0:
            try:
                result = Node.lock_many(count=count, locked_by=locked_by,
                                        machine_type=machine_type,
                                        description=description,
                                        os_type=os_type, os_version=os_version)
                log.info("Locked {names} for {locked_by}".format(
                    names=" ".join([str(node) for node in result]),
                    locked_by=locked_by))
                return result
            except RaceConditionError as exc:
                log.warn("lock_many() detected race condition")
                attempts -= 1
                if attempts > 0:
                    log.info("retrying after race avoidance (%s tries left)",
                             attempts)
                else:
                    error(exc.url, exc.message)
            except PaddlesError as exc:
                error(exc.url, exc.message)

    @expose(generic=True, template='json')
    def unlock_many(self):
        error('/errors/invalid/',
              "this URI only supports POST requests")

    @unlock_many.when(method='POST', template='json')
    def unlock_many_post(self):
        req = request.json
        fields = ['names', 'locked_by']
        if sorted(req.keys()) != sorted(fields):
            error('/errors/invalid/',
                  "must pass these fields: %s" % ', '.join(fields))
        locked_by = req.get('locked_by')
        names = req.get('names')
        if not isinstance(names, list):
            error('/errors/invalid/',
                  "'names' must be a list; got: %s" % str(type(names)))

        base_query = Node.query
        query = base_query.filter(Node.name.in_(names))
        if query.count() != len(names):
            error('/errors/invalid/',
                  "Could not find all nodes!")

        log.info("Unlocking {count} nodes for {locked_by}".format(
            count=len(names), locked_by=locked_by))
        result = []
        for node in query.all():
            result.append(
                NodeController._lock(node,
                                     dict(locked=False, locked_by=locked_by),
                                     'unlock')
            )
        return result

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
        try:
            self.node.update(update)
        except PaddlesError as exc:
            error(exc.url, exc.message)
        return dict()

    @expose(template='json')
    def lock(self):
        if not self.node:
            error(
                '/errors/not_found/',
                'node not found'
            )
        if request.method not in ('PUT', 'POST'):
            error('/errors/invalid/',
                  'this URI only supports PUT and POST requests' +
                  ' but %s was attempted' % request.method)
        node_dict = request.json
        verb_dict = {False: 'unlock', True: 'lock', None: 'check'}
        verb = verb_dict[node_dict.get('locked')]

        return self._lock(self.node, node_dict, verb)

    @staticmethod
    def _lock(node_obj, node_dict, verb):
        locked_by = node_dict.get('locked_by')
        _verb = dict(lock='Lock', unlock='Unlock').get(verb, 'Check')
        log.debug("{verb}ing {node} for {locked_by}".format(
            verb=_verb, node=node_obj, locked_by=locked_by))
        try:
            node_obj.update(node_dict)
            log.info("{verb}ed {node} for {locked_by}".format(
                verb=_verb,
                node=node_obj,
                locked_by=locked_by))
        except PaddlesError as exc:
            error(exc.url, exc.message)
        return node_obj.__json__()

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
