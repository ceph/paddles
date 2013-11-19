from datetime import datetime
from sqlalchemy import Date, cast

from pecan import conf, expose, redirect, request
from paddles.models import Run
from paddles.controllers.jobs import JobsController
from paddles.controllers import error


date_format = '%Y-%m-%d'
datetime_format = '%Y-%m-%d_%H:%M:%S'


def latest_runs(count, fields=None):
    runs = Run.query.order_by(Run.posted.desc()).limit(count).all()
    if fields:
        try:
            return [run.slice(fields) for run in runs]
        except AttributeError:
            error('/errors/invalid/',
                  'an invalid field was specified')
    return [run for run in runs]


def date_from_string(string, fmt=datetime_format):
        try:
            if string == 'today':
                date_str = datetime.utcnow()
                date = date_str.strftime(fmt)
            elif string == 'yesterday':
                date = datetime.utcnow().replace(day=date.day - 1)
                date_str = date.strftime(fmt)
            else:
                date_str = string
                date = datetime.strptime(date_str, fmt)
            return (date, date_str)
        except ValueError:
            error('/errors/invalid/', 'date format must match %s' %
                  date_format)


class RunController(object):
    def __init__(self, name):
        self.name = name
        try:
            self.run = Run.filter_by(name=name).first()
        except ValueError:
            self.run = None
        request.context['run'] = self.run
        request.context['run_name'] = self.name

    @expose(generic=True, template='json')
    def index(self):
        if not self.run:
            error('/errors/not_found/',
                  'requested run resource does not exist')
        json_run = self.run.__json__()
        json_run['jobs'] = self.run.get_jobs()
        return json_run

    @index.when(method='DELETE', template='json')
    def index_delete(self):
        if not self.run:
            error('/errors/not_found/',
                  'attempted to delete a non-existent run')
        self.run.delete()
        return dict()

    jobs = JobsController()


class LatestRunsByCountController(object):
    def __init__(self, count):
        if count == '':
            count = conf.default_latest_runs_count

        try:
            self.count = int(count)
        except ValueError:
            error('/errors/invalid/',
                  "must specify an integer")

    @expose('json')
    def index(self, fields=''):
        return latest_runs(self.count, fields)


class LatestRunsController(object):
    @expose(generic=True, template='json')
    def index(self, fields=''):
        count = conf.default_latest_runs_count
        return latest_runs(count, fields)

    @expose('json')
    def _lookup(self, count, *remainder):
        return LatestRunsByCountController(count), remainder


class SuitesController(object):
    @expose('json')
    def index(self):
        query = request.context.get('query', Run.query)
        return list(set([item[0] for item in query.values(Run.suite) if
                         item[0]]))

    @expose('json')
    def _lookup(self, suite, *remainder):
        return SuiteController(suite), remainder


class BranchesController(object):
    @expose('json')
    def index(self):
        query = request.context.get('query', Run.query)
        return list(set([item[0] for item in query.values(Run.branch) if
                         item[0]]))

    @expose('json')
    def _lookup(self, branch, *remainder):
        return BranchController(branch), remainder


class SuiteController(object):
    def __init__(self, suite):
        self.suite = suite
        base_query = request.context.get('query', Run.query)
        request.context['query'] = base_query.filter(Run.suite == self.suite)

    @expose('json')
    def index(self, count=conf.default_latest_runs_count, since=None):
        query = request.context['query']
        if since:
            since_date = date_from_string(since, fmt=date_format)
            query = query.filter(Run.scheduled > since)
        return query.order_by(Run.scheduled.desc()).limit(count).all()

    branch = BranchesController()


class BranchController(object):
    def __init__(self, branch):
        self.branch = branch
        base_query = request.context.get('query', Run.query)
        request.context['query'] = base_query.filter(Run.branch == self.branch)

    @expose('json')
    def index(self, count=conf.default_latest_runs_count, since=None):
        query = request.context['query']
        if since:
            since_date = date_from_string(since, fmt=date_format)
            query = query.filter(Run.scheduled > since)
        return query.order_by(Run.scheduled.desc()).limit(count).all()

    suite = SuitesController()


class DateRangeController(object):
    def __init__(self, from_date):
        from_date += '_00:00:00'
        (self.from_date, self.from_date_str) = \
            date_from_string(from_date)

    @expose('json')
    def index(self):
        return []

    @expose('json')
    def to(self, to_date):
        to_date += '_23:59:59'
        (self.to_date, self.to_date_str) = \
            date_from_string(to_date)
        base_query = request.context.get('query', Run.query)
        request.context['query'] = base_query.filter(
            Run.scheduled.between(self.from_date, self.to_date))
        return request.context['query'].all()


class DatesController(object):
    @expose('json')
    def index(self):
        query = request.context.get('query', Run.query)
        return list(set(
            [item[0] for item in query.values(cast(Run.scheduled, Date))
             if item[0]]))

    @expose('json')
    def _lookup(self, date, *remainder):
        if date == 'from':
            return DateRangeController(remainder[0]), remainder[1:]
        return DateController(date), remainder


class DateController(object):

    def __init__(self, date):
        (self.date, self.date_str) = date_from_string(date)
        base_query = request.context.get('query', Run.query)
        request.context['query'] = base_query.filter(
            cast(Run.scheduled, Date) == self.date_str)

    @expose('json')
    def index(self, count=conf.default_latest_runs_count):
        return request.context['query'].order_by(
            Run.scheduled.desc()).limit(count).all()


class RunsController(object):
    @expose(generic=True, template='json')
    def index(self, fields=''):
        return latest_runs(conf.default_latest_runs_count, fields)

    @index.when(method='POST', template='json')
    def index_post(self):
        # save to DB here
        try:
            name = request.json.get('name')
        except ValueError:
            error('/errors/invalid/', 'could not decode JSON body')
        if not name:
            error('/errors/invalid/', "could not find required key: 'name'")
        if not Run.filter_by(name=name).first():
            new_run = Run(name)
            return dict()
        else:
            error('/errors/invalid/', "run with name %s already exists" % name)

    latest = LatestRunsController()

    branch = BranchesController()

    suite = SuitesController()

    date = DatesController()

    @expose('json')
    def _lookup(self, name, *remainder):
        return RunController(name), remainder
