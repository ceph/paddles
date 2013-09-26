from pecan import expose, abort, request
from paddles.models import Run


class RunController(object):

    def __init__(self, job_id):
        self.job_id = job_id
        try:
            self.run = Run.filter_by(job_id=job_id).first()
        except ValueError:
            self.run = None
        # grab this guy from DB

    @expose('json')
    def index(self):
        # return JSON repr of the database obj
        # with jsonify
        if not self.run:
            abort(404)
        return self.run
        return dict()


class RunsController(object):

    @expose(generic=True)
    def index(self):
        return dict()

    @index.when(method='POST', template='json')
    def index_post(self):
        # save to DB here
        new_run = Run(request.json)
        return dict()

    @expose('json')
    def _lookup(self, _id, *remainder):
        return RunController(_id), remainder

