import logging

from pecan import abort, conf, expose, request
from sqlalchemy import Date, cast, select

from paddles.controllers import create_run, date_format, date_from_string, error
from paddles.controllers.jobs import JobsController
from paddles.controllers.util import offset_query
from paddles.decorators import retryOperation
from paddles.models import Job, Run, Session, rollback

log = logging.getLogger(__name__)


def latest_runs(fields=None, count=conf.default_latest_runs_count, page=1):
    query = select(Run).order_by(Run.posted.desc())
    query = offset_query(query, page_size=count, page=page)
    runs = Session.scalars(query).all()
    if fields:
        try:
            return [run.slice(fields) for run in runs]
        except AttributeError:
            rollback()
            error("/errors/invalid/", "an invalid field was specified")
    return runs


class RunController(object):
    def __init__(self, name):
        self.name = name
        request.context["run_name"] = self.name
        self.run = self._find_run(name)

    # @retryOperation(exceptions=(OperationalError, InvalidRequestError))
    def _find_run(self, name):
        return Session.scalars(select(Run).filter_by(name=name)).first()

    @expose(generic=True, template="json")
    @retryOperation
    def index(self):
        if not self.run:
            abort(404)
        json_run = self.run.__json__()
        json_run["jobs"] = self.run.get_jobs()
        return json_run

    @index.when(method="DELETE", template="json")
    def index_delete(self):
        if not self.run:
            error("/errors/not_found/", "attempted to delete a non-existent run")
        log.info("Deleting run: %r", self.run)
        Session.delete(self.run)
        return dict()

    jobs = JobsController()


class RunFilterIndexController(object):
    """
    Base class for index controllers
    FIXME what is that
    Must be subclassed.
    """

    def get_subquery(self, query):
        return query

    def get_lookup_controller(self):
        raise NotImplementedError

    @expose("json")
    @retryOperation
    def index(self):
        query = request.context.get("query", select(Run))
        return sorted(list(Session.scalars(self.get_subquery(query))))

    @expose("json")
    def _lookup(self, value, *remainder):
        return self.get_lookup_controller()(value), remainder


class BranchesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(Run.branch)

    def get_lookup_controller(self):
        return BranchController


class DatesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(cast(Run.scheduled, Date))

    @expose("json")
    def _lookup(self, date, *remainder):
        if date == "from":
            return DateRangeController(remainder[0]), remainder[1:]
        return DateController(date), remainder


class MachineTypesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(Run.machine_type)

    def get_lookup_controller(self):
        return MachineTypeController


class FlavorsController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(Job.flavor)

    def get_lookup_controller(self):
        return FlavorController


class SuitesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(Run.suite)

    def get_lookup_controller(self):
        return SuiteController


class UsersController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(Run.user)

    def get_lookup_controller(self):
        return UserController


class StatusesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(Run.status)

    def get_lookup_controller(self):
        return StatusController


class RunFilterController(object):
    def __init__(self, value):
        self.value = value
        base_query = request.context.get("query", select(Run))
        subquery = self.get_subquery(base_query)
        request.context["query"] = subquery

    def get_subquery(self, query):
        return query

    @expose("json")
    @retryOperation
    def index(self, count=conf.default_latest_runs_count, page=1, since=None):
        query = request.context["query"]
        if since:
            since = date_from_string(since, out_fmt=date_format)[1]
            query = query.filter(Run.scheduled > since)
        query = query.order_by(Run.scheduled.desc())
        return list(Session.scalars(offset_query(query, count, page)))

    def get_lookup_controller(self, field: str):
        raise NotImplementedError

    @expose("json")
    def _lookup(self, field, *remainder):
        return self.get_lookup_controller(field), remainder


class BranchController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.branch == self.value)

    def get_lookup_controller(self, field: str):
        if field == "date":
            return DatesController()
        if field == "machine_type":
            return MachineTypesController()
        if field == "sha1":
            return Sha1sController()
        if field == "status":
            return StatusesController()
        if field == "suite":
            return SuitesController()
        if field == "user":
            return UsersController()
        if field == "flavor":
            return FlavorsController()


class DateController(RunFilterController):
    def get_subquery(self, query):
        (self.from_date, self.from_date_str) = date_from_string(
            self.value, hours="00:00:00"
        )
        (self.to_date, self.to_date_str) = date_from_string(
            self.value, hours="23:59:59"
        )
        return query.filter(Run.scheduled.between(self.from_date, self.to_date))

    @expose("json")
    def index(self, count=conf.default_latest_runs_count, page=1):
        query = request.context["query"].order_by(Run.scheduled.desc())
        return list(Session.scalars(offset_query(query, count, page)))

    def get_lookup_controller(self, field: str):
        if field == "branch":
            return BranchesController()
        if field == "machine_type":
            return MachineTypesController()
        if field == "status":
            return StatusesController()
        if field == "sha1":
            return Sha1sController()
        if field == "suite":
            return SuitesController()
        if field == "user":
            return UsersController()
        if field == "flavor":
            return FlavorsController()


class MachineTypeController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.machine_type == self.value)

    def get_lookup_controller(self, field: str):
        if field == "branch":
            return BranchesController()
        if field == "date":
            return DatesController()
        if field == "status":
            return StatusesController()
        if field == "sha1":
            return Sha1sController()
        if field == "suite":
            return SuitesController()
        if field == "user":
            return UsersController()
        if field == "flavor":
            return FlavorsController()


class StatusController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.status == self.value)

    def get_lookup_controller(self, field: str):
        if field == "branch":
            return BranchesController()
        if field == "date":
            return DatesController()
        if field == "machine_type":
            return MachineTypesController()
        if field == "sha1":
            return Sha1sController()
        if field == "suite":
            return SuitesController()
        if field == "user":
            return UsersController()
        if field == "flavor":
            return FlavorsController()


class SuiteController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.suite == self.value)

    def get_lookup_controller(self, field: str):
        if field == "branch":
            return BranchesController()
        if field == "date":
            return DatesController()
        if field == "machine_type":
            return MachineTypesController()
        if field == "sha1":
            return Sha1sController()
        if field == "status":
            return StatusesController()
        if field == "user":
            return UsersController()
        if field == "flavor":
            return FlavorsController()


class UserController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.user == self.value)

    def get_lookup_controller(self, field: str):
        if field == "branch":
            return BranchesController()
        if field == "date":
            return DatesController()
        if field == "machine_type":
            return MachineTypesController()
        if field == "sha1":
            return Sha1sController()
        if field == "status":
            return StatusesController()
        if field == "suite":
            return SuitesController()
        if field == "flavor":
            return FlavorsController()


class FlavorController(RunFilterController):
    def get_subquery(self, query):
        return query.join(Job).filter(Job.flavor == self.value).group_by(Run)

    def get_lookup_controller(self, field: str):
        if field == "branch":
            return BranchesController()
        if field == "date":
            return DatesController()
        if field == "machine_type":
            return MachineTypesController()
        if field == "sha1":
            return Sha1sController()
        if field == "status":
            return StatusesController()
        if field == "suite":
            return SuitesController()
        if field == "user":
            return UsersController()


class DateRangeController(object):
    def __init__(self, from_date):
        (self.from_date, self.from_date_str) = date_from_string(from_date)

    @expose("json")
    def index(self):
        return []

    @expose("json")
    def to(self, to_date):
        (self.to_date, self.to_date_str) = date_from_string(to_date, hours="23:59:59")
        base_query = request.context.get("query", select(Run))
        request.context["query"] = base_query.filter(
            Run.scheduled.between(self.from_date, self.to_date)
        )
        return Session.scalars(request.context["query"]).all()


class QueuedRunsController(object):
    @expose("json")
    def index(self):
        query = (
            Session.query(Run)
            .join(Job)
            .filter(Job.status == "queued")
            .group_by(Run)
            .order_by(Run.scheduled)
        )
        return query.all()


class Sha1sController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.with_only_columns(Job.sha1)

    def get_lookup_controller(self):
        return Sha1Controller


class Sha1Controller(RunFilterController):
    def get_subquery(self, query):
        return query.join(Job).filter(Job.sha1.startswith(self.value)).group_by(Run)

    def get_lookup_controller(self, field: str):
        if field == "branch":
            return BranchesController()
        if field == "date":
            return DatesController()
        if field == "machine_type":
            return MachineTypesController()
        if field == "status":
            return StatusesController()
        if field == "suite":
            return SuitesController()
        if field == "user":
            return UsersController()
        if field == "flavor":
            return FlavorsController()


class RunsController(object):
    @expose(generic=True, template="json")
    def index(self, fields="", count=conf.default_latest_runs_count, page=1):
        return latest_runs(fields=fields, count=count, page=page)

    @index.when(method="POST", template="json")
    def index_post(self):
        # save to DB here
        try:
            name = request.json.get("name")
        except ValueError:
            rollback()
            error("/errors/invalid/", "could not decode JSON body")
        if not name:
            error("/errors/invalid/", "could not find required key: 'name'")
        if not Session.scalars(select(Run).filter_by(name=name)).first():
            create_run(name)
            return dict()
        else:
            error("/errors/invalid/", "run with name %s already exists" % name)

    @classmethod
    @retryOperation
    def _create_run(cls, name):
        log.info("Creating run: %s", name)
        with Session.no_autoflush:
            run = Run(name)
            Session.add(run)
            return run

    branch = BranchesController()

    date = DatesController()

    machine_type = MachineTypesController()

    status = StatusesController()

    suite = SuitesController()

    queued = QueuedRunsController()

    sha1 = Sha1sController()

    user = UsersController()

    flavors = FlavorsController()

    @expose("json")
    def _lookup(self, name, *remainder):
        return RunController(name), remainder
