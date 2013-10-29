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


class RunsByFieldValueController(object):
    def __init__(self, field_name, value, base_query=None):
        self.field_name = field_name
        self.field = getattr(Run, field_name)
        self.value = value
        if not base_query:
            base_query = Run.query
        #self.base_query = base_query
        self.base_query = base_query.filter(self.field == self.value)

    @expose(generic=True, template='json')
    def index(self):
        return self.base_query.all()
        #return self.base_query.filter(self.field == self.value).all()


class RunsByFieldController(object):
    def __init__(self, field_name, value_controller=RunsByFieldValueController,
                 base_query=None):
        self.field_name = field_name
        self.field = getattr(Run, field_name)
        self.value_controller = value_controller
        if not base_query:
            base_query = Run.query
        self.base_query = base_query

    @expose(generic=True, template='json')
    def index(self):
        return list(set([item[0] for item in self.base_query.values(self.field)
                         if item[0]]))

    @expose('json')
    def _lookup(self, value, *remainder):
        return (self.value_controller(
            self.field_name,
            value,
            self.base_query),
            remainder)


class RunsBySuiteController(RunsByFieldController):
    def __init__(self, base_query=None):
        self.field_name = 'suite'
        supercls = super(RunsBySuiteController, self)
        supercls.__init__(self.field_name, RunsByFieldValueController,
                          base_query)


class RunsByBranchValueController(RunsByFieldValueController):
    @property
    def suite(self):
        return RunsBySuiteController(self.base_query)


class RunsByBranchController(RunsByFieldController):
    def __init__(self, base_query=None):
        self.field_name = 'branch'
        supercls = super(RunsByBranchController, self)
        supercls.__init__(self.field_name, RunsByBranchValueController,
                          base_query)


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

    branch = RunsByBranchController()

    suite = RunsBySuiteController()

    @expose('json')
    def _lookup(self, name, *remainder):
        return RunController(name), remainder
