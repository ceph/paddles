import logging
import datetime
from sqlalchemy import Date, cast
from sqlalchemy.exc import InvalidRequestError, OperationalError

from pecan import abort, conf, expose, request
from paddles.models import Job, Run, rollback, Session, TEUTHOLOGY_TIMESTAMP_FMT
from paddles.controllers.jobs import JobsController
from paddles.controllers.util import offset_query
from paddles.controllers import error
from paddles.decorators import retryOperation

log = logging.getLogger(__name__)

date_format = '%Y-%m-%d'


def latest_runs(fields=None, count=conf.default_latest_runs_count, page=1):
    query = Run.query.order_by(Run.posted.desc())
    query = offset_query(query, page_size=count, page=page)
    runs = list(query)
    if fields:
        try:
            return [run.slice(fields) for run in runs]
        except AttributeError:
            rollback()
            error('/errors/invalid/',
                  'an invalid field was specified')
    return [run for run in runs]


def date_from_string(date_str, out_fmt=TEUTHOLOGY_TIMESTAMP_FMT, hours='00:00:00'):
        try:
            if date_str == 'today':
                date = datetime.date.today()
                date_str = date.strftime(date_format)
            elif date_str == 'yesterday':
                date = datetime.date.today()
                date = date.replace(day=date.day - 1)
                date_str = date.strftime(date_format)
            else:
                date = datetime.datetime.strptime(date_str, date_format)

            if out_fmt == TEUTHOLOGY_TIMESTAMP_FMT:
                date_str = '{date}_{time}'.format(date=date_str, time=hours)
                date = datetime.datetime.strptime(date_str, out_fmt)

            return (date, date_str)
        except ValueError:
            rollback()
            error('/errors/invalid/', 'date format must match %s' %
                  date_format)


class RunController(object):
    def __init__(self, name):
        self.name = name
        request.context['run_name'] = self.name
        self.run = self._find_run(name)

    @retryOperation(exceptions=(OperationalError, InvalidRequestError))
    def _find_run(self, name):
        return Run.query.filter_by(name=name).first()

    @expose(generic=True, template='json')
    @retryOperation
    def index(self):
        if not self.run:
            abort(404)
        json_run = self.run.__json__()
        json_run['jobs'] = self.run.get_jobs()
        return json_run

    @index.when(method='DELETE', template='json')
    def index_delete(self):
        if not self.run:
            error('/errors/not_found/',
                  'attempted to delete a non-existent run')
        log.info("Deleting run: %r", self.run)
        self.run.delete()
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

    @expose('json')
    @retryOperation
    def index(self):
        query = request.context.get('query', Run.query)
        subquery = self.get_subquery(query)
        return sorted(list(set([item[0] for item in subquery if item[0]])))

    @expose('json')
    def _lookup(self, value, *remainder):
        return self.get_lookup_controller()(value), remainder


class BranchesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.values(Run.branch)

    def get_lookup_controller(self):
        return BranchController


class DatesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.values(cast(Run.scheduled, Date))

    @expose('json')
    def _lookup(self, date, *remainder):
        if date == 'from':
            return DateRangeController(remainder[0]), remainder[1:]
        return DateController(date), remainder


class MachineTypesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.values(Run.machine_type)

    def get_lookup_controller(self):
        return MachineTypeController


class SuitesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.values(Run.suite)

    def get_lookup_controller(self):
        return SuiteController


class UsersController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.values(Run.user)

    def get_lookup_controller(self):
        return UserController


class StatusesController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.values(Run.status)

    def get_lookup_controller(self):
        return StatusController


class RunFilterController(RunFilterIndexController):
    def __init__(self, value):
        self.value = value
        base_query = request.context.get('query', Run.query)
        subquery = self.get_subquery(base_query)
        request.context['query'] = subquery

    @expose('json')
    @retryOperation
    def index(self, count=conf.default_latest_runs_count, page=1, since=None):
        query = request.context['query']
        if since:
            since = date_from_string(since, out_fmt=date_format)[1]
            query = query.filter(Run.scheduled > since)
        query = query.order_by(Run.scheduled.desc())
        return list(offset_query(query, count, page))
    @expose('json')
    def _lookup(self, field, *remainder):
        return self.get_lookup_controller(field), remainder


class BranchController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.branch == self.value)

    def get_lookup_controller(self, field):
        if field == 'date':
            return DatesController()
        if field == 'machine_type':
            return MachineTypesController()
        if field == 'sha1':
            return Sha1sController()
        if field == 'status':
            return StatusesController()
        if field == 'suite':
            return SuitesController()
        if field == 'user':
            return UsersController()


class DateController(RunFilterController):
    def get_subquery(self, query):
        (self.from_date, self.from_date_str) = \
            date_from_string(self.value, hours='00:00:00')
        (self.to_date, self.to_date_str) = \
            date_from_string(self.value, hours='23:59:59')
        return query.filter(Run.scheduled.between(self.from_date, self.to_date))

    @expose('json')
    def index(self, count=conf.default_latest_runs_count, page=1):
        query = request.context['query'].order_by(Run.scheduled.desc())
        return list(offset_query(query, count, page))

    def get_lookup_controller(self, field):
        if field == 'branch':
            return BranchesController()
        if field == 'machine_type':
            return MachineTypesController()
        if field == 'status':
            return StatusesController()
        if field == 'sha1':
            return Sha1sController()
        if field == 'suite':
            return SuitesController()
        if field == 'user':
            return UsersController()


class MachineTypeController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.machine_type == self.value)

    def get_lookup_controller(self, field):
        if field == 'branch':
            return BranchesController()
        if field == 'date':
            return DatesController()
        if field == 'status':
            return StatusesController()
        if field == 'sha1':
            return Sha1sController()
        if field == 'suite':
            return SuitesController()
        if field == 'user':
            return UsersController()


class StatusController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.status == self.value)

    def get_lookup_controller(self, field):
        if field == 'branch':
            return BranchesController()
        if field == 'date':
            return DatesController()
        if field == 'machine_type':
            return MachineTypesController()
        if field == 'sha1':
            return Sha1sController()
        if field == 'suite':
            return SuitesController()
        if field == 'user':
            return UsersController()


class SuiteController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.suite == self.value)

    def get_lookup_controller(self, field):
        if field == 'branch':
            return BranchesController()
        if field == 'date':
            return DatesController()
        if field == 'machine_type':
            return MachineTypesController()
        if field == 'sha1':
            return Sha1sController()
        if field == 'status':
            return StatusesController()
        if field == 'user':
            return UsersController()


class UserController(RunFilterController):
    def get_subquery(self, query):
        return query.filter(Run.user == self.value)

    def get_lookup_controller(self, field):
        if field == 'branch':
            return BranchesController()
        if field == 'date':
            return DatesController()
        if field == 'machine_type':
            return MachineTypesController()
        if field == 'sha1':
            return Sha1sController()
        if field == 'status':
            return StatusesController()
        if field == 'suite':
            return SuitesController()


class DateRangeController(object):
    def __init__(self, from_date):
        (self.from_date, self.from_date_str) = \
            date_from_string(from_date)

    @expose('json')
    def index(self):
        return []

    @expose('json')
    def to(self, to_date):
        (self.to_date, self.to_date_str) = \
            date_from_string(to_date, hours='23:59:59')
        base_query = request.context.get('query', Run.query)
        request.context['query'] = base_query.filter(
            Run.scheduled.between(self.from_date, self.to_date))
        return request.context['query'].all()


class QueuedRunsController(object):
    @expose('json')
    def index(self):
        query = Session.query(Run).join(Job).filter(Job.status == 'queued')\
            .group_by(Run).order_by(Run.scheduled)
        return query.all()

class Sha1sController(RunFilterIndexController):
    def get_subquery(self, query):
        return query.values(Job.sha1)

    def get_lookup_controller(self):
        return Sha1Controller


class Sha1Controller(RunFilterController):
    def get_subquery(self, query):
        return query.join(Job).filter(Job.sha1.startswith(self.value))\
                .group_by(Run)

    def get_lookup_controller(self, field):
        if field == 'branch':
            return BranchesController()
        if field == 'date':
            return DatesController()
        if field == 'machine_type':
            return MachineTypesController()
        if field == 'status':
            return StatusesController()
        if field == 'suite':
            return SuitesController()
        if field == 'user':
            return UsersController()



class RunsController(object):
    @expose(generic=True, template='json')
    def index(self, fields='', count=conf.default_latest_runs_count, page=1):
        return latest_runs(fields=fields, count=count, page=page)

    @index.when(method='POST', template='json')
    def index_post(self):
        # save to DB here
        try:
            name = request.json.get('name')
        except ValueError:
            rollback()
            error('/errors/invalid/', 'could not decode JSON body')
        if not name:
            error('/errors/invalid/', "could not find required key: 'name'")
        if not Run.query.filter_by(name=name).first():
            self._create_run(name)
            return dict()
        else:
            error('/errors/invalid/', "run with name %s already exists" % name)

    @classmethod
    @retryOperation
    def _create_run(cls, name):
        log.info("Creating run: %s", name)
        Session.flush()
        return Run(name)

    branch = BranchesController()

    date = DatesController()

    machine_type = MachineTypesController()

    status = StatusesController()

    suite = SuitesController()

    queued = QueuedRunsController()

    sha1 = Sha1sController()

    user = UsersController()

    @expose('json')
    def _lookup(self, name, *remainder):
        return RunController(name), remainder
