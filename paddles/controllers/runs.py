from pecan import expose, abort, request
from paddles.models import Run, Job


class RunController(object):

    def __init__(self, name):
        self.name = name
        try:
            self.run = Run.filter_by(name=name).first()
        except ValueError:
            self.run = None

    @expose(generic=True, template='json')
    def index(self):
        if not self.run:
            abort(404)
        return self.run

    @index.when(method='POST', template='json')
    def index_post(self):
        # save to DB here
        new_run = Job(request.json)
        return dict()

    @expose('json')
    def _lookup(self, job_id, *remainder):
        return JobController(job_id), remainder


class RunsController(object):

    @expose(generic=True, template='json')
    def index(self):
        return Run.query.limit(10).all()

    @index.when(method='POST', template='json')
    def index_post(self):
        # save to DB here
        name = request.json.get('name')
        if not name:
            abort(400)
        new_run = Run(name)
        return dict()

    @expose('json')
    def _lookup(self, name, *remainder):
        return RunController(name), remainder
