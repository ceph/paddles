import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from pecan import abort, expose, request
from sqlalchemy import func, select
from sqlalchemy.exc import InvalidRequestError, OperationalError
from sqlalchemy.orm import aliased, load_only

from paddles.controllers import error
from paddles.controllers.util import offset_query
from paddles.decorators import retryOperation
from paddles.exceptions import PaddlesError
from paddles.models import Job, Node
from paddles.models.job_nodes import job_nodes_table
from paddles.util import coerce_bool

log = logging.getLogger(__name__)


class NodesController(object):
    @expose(generic=True, template="json")
    @retryOperation
    def index(
        self,
        locked=None,
        machine_type="",
        os_type=None,
        os_version=None,
        locked_by=None,
        up=None,
        count=None,
    ):
        locked = coerce_bool(locked)
        up = coerce_bool(up)
        query = select(Node)
        if locked is not None:
            query = query.filter(Node.locked == locked)
        if machine_type:
            if "|" in machine_type:
                machine_types = machine_type.split("|")
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
            try:
                count = int(count)
            except (TypeError, ValueError):
                error("/errors/invalid/", "count must be an integer")
            query = query.limit(count)
        return [node.__json__() for node in self._find_nodes(query)]

    @retryOperation(exceptions=(OperationalError, InvalidRequestError))
    def _find_nodes(self, query):
        return request.session.scalars(query).all()

    @retryOperation(exceptions=(OperationalError, InvalidRequestError))
    @index.when(method="POST", template="json")
    def index_post(self):
        """
        Create a new node
        """
        session = request.session
        try:
            data = request.json
            name = data.get("name")
        except ValueError:
            session.rollback()
            error("/errors/invalid/", "could not decode JSON body")
        # we allow empty data to be pushed
        if not name:
            error("/errors/invalid/", "could not find required key: 'name'")

        if session.execute(select(Node).filter_by(name=name)).first():
            error("/errors/invalid/", "Node with name %s already exists" % name)
        else:
            self.node = Node(name=name)
            try:
                self.node.update(data)
            except PaddlesError as exc:
                error(exc.url, str(exc))
            session.add(self.node)
            session.commit()
            log.info(
                "Created {node}: {data}".format(
                    node=self.node,
                    data=data,
                )
            )
        return dict()

    @expose(generic=True, template="json")
    def lock_many(self):
        error("/errors/invalid/", "this URI only supports POST requests")

    @lock_many.when(method="POST", template="json")
    @retryOperation
    def lock_many_post(self):
        req = request.json
        fields = set(("count", "locked_by", "machine_type", "description"))
        if not fields.issubset(set(req.keys())):
            error("/errors/invalid/", "must pass these fields: %s" % ", ".join(fields))

        req["locked"] = True

        count = req.pop("count", 0)
        if count < 1:
            error("/errors/invalid/", "cannot lock less than 1 node")

        machine_type = req.pop("machine_type", None)
        if not machine_type:
            error("/errors/invalid/", "must specify machine_type")

        locked_by = req.get("locked_by")
        description = req.get("description")
        os_type = req.get("os_type")
        os_version = req.get("os_version")
        arch = req.get("arch")
        if os_version is not None:
            os_version = str(os_version)
        attempts = 2
        log.debug(
            "Locking {count} {mtype} nodes for {locked_by}".format(
                count=count, mtype=machine_type, locked_by=locked_by
            )
        )
        while attempts > 0:
            try:
                result = Node.lock_many(
                    count=count,
                    locked_by=locked_by,
                    machine_type=machine_type,
                    description=description,
                    os_type=os_type,
                    os_version=os_version,
                    arch=arch,
                )
                if description:
                    desc_str = " with description %s" % description
                else:
                    desc_str = ""
                log.info(
                    "Locked {names} for {locked_by}{desc_str}".format(
                        names=" ".join([str(node) for node in result]),
                        locked_by=locked_by,
                        desc_str=desc_str,
                    )
                )
                request.session.commit()
                return result
            except PaddlesError as exc:
                error(exc.url, str(exc))
                raise
                # request.session.rollback()
            except (OperationalError, InvalidRequestError):
                attempts -= 1
                request.session.rollback()
                if attempts <= 0:
                    raise

    @expose(generic=True, template="json")
    def unlock_many(self):
        error("/errors/invalid/", "this URI only supports POST requests")

    @unlock_many.when(method="POST", template="json")
    @retryOperation
    def unlock_many_post(self):
        session = request.session
        req = request.json
        fields = ["names", "locked_by"]
        if sorted(req.keys()) != sorted(fields):
            error("/errors/invalid/", "must pass these fields: %s" % ", ".join(fields))
        locked_by = req.get("locked_by")
        names = req.get("names")
        if not isinstance(names, list):
            error(
                "/errors/invalid/", "'names' must be a list; got: %s" % str(type(names))
            )

        # if len(result) != len(names):
        if session.scalar(
            select(func.count()).select_from(Node).where(Node.name.in_(names))
        ) != len(names):
            error("/errors/invalid/", "Could not find all nodes!")

        log.info(
            "Unlocking {count} nodes for {locked_by}".format(
                count=len(names), locked_by=locked_by
            )
        )
        result = []
        for node in session.scalars(select(Node).filter(Node.name.in_(names))).all():
            # for node in result:
            result.append(
                NodeController._lock(
                    node, dict(locked=False, locked_by=locked_by), "unlock"
                )
            )
        return result

    @expose("json")
    def job_stats(self, machine_type="", since_days=14):
        since_days = int(since_days)
        if since_days < 1:
            error("/errors/invalid/", "since_days must be a positive integer")

        now = datetime.now(timezone.utc)
        past = now - timedelta(days=since_days)
        recent_jobs = select(Job).where(Job.posted.between(past, now)).subquery()
        RecentJob = aliased(Job, recent_jobs)

        query = (
            select(Node.name, RecentJob.status, func.count())
            .select_from(Node)
            .join(job_nodes_table, Node.id == job_nodes_table.c.node_id)
            .join(RecentJob, RecentJob.id == job_nodes_table.c.job_id)
        )

        if machine_type:
            # Note: filtering by Job.machine_type (as below) greatly improves
            # performance but could lead slightly incorrect values if many jobs
            # are being scheduled using mixed machine types. We work around
            # this by including the 'multi' machine type (which is the name of
            # the queue Inktank uses for such jobs.
            query = query.where(RecentJob.machine_type.in_((machine_type, "multi")))
            query = query.where(Node.machine_type == machine_type)

        query = query.group_by(Node.name, RecentJob.status)

        all_stats = {}
        results = request.session.execute(query).all()
        for name, status, count in results:
            node_stats = all_stats.get(name, {})
            node_stats[status] = count
            all_stats[name] = node_stats

        ordered_stats = OrderedDict(
            sorted(
                all_stats.items(),
                key=lambda t: sum(t[1].values()),
            )
        )
        return ordered_stats

    @expose("json")
    def machine_types(self):
        query = select(Node).with_only_columns(Node.machine_type)
        result = request.session.execute(query).all()
        return sorted(list(set([item[0] for item in result if item[0]])))

    @expose("json")
    def _lookup(self, name, *remainder):
        return NodeController(name), remainder or ("",)


class NodeController(object):
    def __init__(self, name):
        self.name = name
        self.node = self._find_node(name)
        request.context["node_name"] = self.name

    @retryOperation(exceptions=(OperationalError, InvalidRequestError))
    def _find_node(self, name):
        node_q = (
            select(Node)
            .options(load_only(Node.id, Node.name))
            .filter(Node.name == name)
        )
        return request.session.scalars(node_q).one_or_none()

    @expose(generic=True, template="json")
    def index(self):
        if not self.node:
            error("/errors/not_found/", "node not found")
        json_node = self.node.__json__()
        return json_node

    @index.when(method="PUT", template="json")
    def index_put(self):
        """
        Update the Node object here
        """
        if not self.node:
            error("/errors/not_found/", "attempted to update a non-existent node")
        update = request.json
        log.info(
            "Updating {node}: {data}".format(
                node=self.node,
                data=update,
            )
        )
        self.node.update(update)
        request.session.commit()
        return dict()

    @index.when(method="DELETE", template="json")
    def index_delete(self):
        session = request.session
        if not self.node:
            error("/errors/not_found/", "node not found")
        log.info("Deleting node %r", self.node)
        session.delete(self.node)
        session.commit()
        return dict()

    @expose(template="json")
    def lock(self):
        if not self.node:
            error("/errors/not_found/", "node not found")
        if request.method not in ("PUT", "POST"):
            error(
                "/errors/invalid/",
                "this URI only supports PUT and POST requests"
                + " but %s was attempted" % request.method,
            )
        node_dict = request.json
        verb_dict = {False: "unlock", True: "lock", None: "check"}
        verb = verb_dict[node_dict.get("locked")]
        return self._lock(self.node, node_dict, verb)

    @staticmethod
    @retryOperation
    def _lock(node_obj, node_dict, verb):
        locked_by = node_dict.get("locked_by")
        _verb = dict(lock="Lock", unlock="Unlock").get(verb, "Check")
        description = node_dict.get("description")
        desc_str = " with description %s" % description if description else ""
        log.debug(
            "{verb}ing {node} for {locked_by}{desc_str}".format(
                verb=_verb, node=node_obj, locked_by=locked_by, desc_str=desc_str
            )
        )
        try:
            node_obj.update(node_dict)
            request.session.commit()
            log.info(
                "{verb}ed {node} for {locked_by}{desc_str}".format(
                    verb=_verb,
                    node=node_obj,
                    locked_by=locked_by,
                    desc_str=desc_str,
                )
            )
        except PaddlesError as exc:
            error(exc.url, str(exc))
        return dict(
            name=node_obj.name,
            locked=node_obj.locked,
            locked_by=node_obj.locked_by,
            machine_type=node_obj.machine_type,
            is_vm=node_obj.is_vm,
        )

    @expose("json")
    def jobs(self, name="", status="", count=0, page=1):
        if not self.node:
            abort(404)
        jobs = (
            select(Job)
            .where(Job.target_nodes.contains(self.node))
            .order_by(Job.posted.desc())
        )
        if name:
            jobs = jobs.filter(Job.name == name)
        if status:
            jobs = jobs.filter(Job.status == status)
        if count:
            jobs = offset_query(jobs, count, page)
        return [job.__json__() for job in request.session.scalars(jobs).all()]

    @expose("json")
    def job_stats(self):
        if not self.node:
            abort(404)
        all_jobs = (
            select(func.count())
            .select_from(Job)
            .where(Job.target_nodes.contains(self.node))
        )
        stats = dict()
        for status in Job.allowed_statuses:
            stats[status] = request.session.scalar(all_jobs.filter(Job.status == status))
        return stats
