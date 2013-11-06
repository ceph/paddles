from datetime import datetime
from sqlalchemy import Date, cast

from pecan import conf, expose, redirect, request
from paddles.models import Run
from paddles.controllers.jobs import JobsController
from paddles.controllers import error


def latest_runs(count, fields=None):
    runs = Run.query.order_by(Run.posted.desc()).limit(count).all()
    if fields:
        try:
            return [run.slice(fields) for run in runs]
        except AttributeError:
            error('/errors/invalid/',
                  'an invalid field was specified')
    return [run for run in runs]


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
    def index(self, count=conf.default_latest_runs_count):
        return request.context['query'].order_by(
            Run.scheduled.desc()).limit(count).all()

    branch = BranchesController()


class BranchController(object):
    def __init__(self, branch):
        self.branch = branch
        base_query = request.context.get('query', Run.query)
        request.context['query'] = base_query.filter(Run.branch == self.branch)

    @expose('json')
    def index(self, count=conf.default_latest_runs_count):
        return request.context['query'].order_by(
            Run.scheduled.desc()).limit(count).all()

    suite = SuitesController()


class DatesController(object):
    @expose('json')
    def index(self):
        query = request.context.get('query', Run.query)
        return list(set(
            [item[0] for item in query.values(cast(Run.scheduled, Date))
             if item[0]]))

    @expose('json')
    def _lookup(self, date, *remainder):
        return DateController(date), remainder


class DateController(object):
    date_format = '%Y-%m-%d'

    def __init__(self, date):
        try:
            self.date = datetime.strptime(date, self.date_format)
            self.date_str = date
        except ValueError:
            error('/errors/invalid/', 'date format must match %s' %
                  self.date_format)
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
