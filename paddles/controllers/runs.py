import logging
import datetime
from sqlalchemy import Date, cast
from pecan.ext.notario import validate

from pecan import abort, conf, expose, request
from paddles.models import Job, Run, rollback, Session
from paddles.controllers.jobs import JobsController
from paddles.controllers.util import offset_query
from paddles.controllers import error
from paddles import schemas

log = logging.getLogger(__name__)

date_format = '%Y-%m-%d'
datetime_format = '%Y-%m-%d_%H:%M:%S'


def latest_runs(fields=None, count=conf.default_latest_runs_count, page=1):
    query = Run.query.order_by(Run.posted.desc())
    query = offset_query(query, page_size=count, page=page)
    runs = query.all()
    if fields:
        try:
            return [run.slice(fields) for run in runs]
        except AttributeError:
            rollback()
            error('/errors/invalid/',
                  'an invalid field was specified')
    return [run for run in runs]


def date_from_string(date_str, out_fmt=datetime_format, hours='00:00:00'):
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

            if out_fmt == datetime_format:
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
        self.run = Run.query.filter_by(name=name).first()
        request.context['run_name'] = self.name

    @expose(generic=True, template='json')
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
    def index(self, count=conf.default_latest_runs_count, page=1, since=None):
        query = request.context['query']
        if since:
            since = date_from_string(since, out_fmt=date_format)[1]
            query = query.filter(Run.scheduled > since)
        query = query.order_by(Run.scheduled.desc())
        return offset_query(query, count, page).all()

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
        if field == 'status':
            return StatusesController()
        if field == 'suite':
            return SuitesController()


class DateController(RunFilterController):
    def get_subquery(self, query):
        (self.date, self.date_str) = \
            date_from_string(self.value, out_fmt=date_format)
        return query.filter(cast(Run.scheduled, Date) == self.date_str)

    @expose('json')
    def index(self, count=conf.default_latest_runs_count, page=1):
        query = request.context['query'].order_by(Run.scheduled.desc())
        return offset_query(query, count, page).all()

    def get_lookup_controller(self, field):
        if field == 'branch':
            return BranchesController()
        if field == 'machine_type':
            return MachineTypesController()
        if field == 'status':
            return StatusesController()
        if field == 'suite':
            return SuitesController()


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
        if field == 'suite':
            return SuitesController()


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
        if field == 'suite':
            return SuitesController()


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
        if field == 'status':
            return StatusesController()


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


class RunsController(object):
    @expose(generic=True, template='json')
    def index(self, fields='', count=conf.default_latest_runs_count, page=1):
        return latest_runs(fields=fields, count=count, page=page)

    @index.when(method='POST', template='json')
    @validate(schemas.run_schema(), handler='/errors/schema')
    def index_post(self):
        name = request.json.get('name')
        if not Run.query.filter_by(name=name).first():
            log.info("Creating run: %s", name)
            Run(name)
            return dict()
        else:
            error('/errors/invalid/', "run with name %s already exists" % name)

    branch = BranchesController()

    date = DatesController()

    machine_type = MachineTypesController()

    status = StatusesController()

    suite = SuitesController()

    queued = QueuedRunsController()

    @expose('json')
    def _lookup(self, name, *remainder):
        return RunController(name), remainder
