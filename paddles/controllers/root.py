from pecan import expose

from paddles.controllers.runs import RunsController
from paddles.controllers.errors import ErrorsController
from paddles.models import Run, Job


class RootController(object):

    @expose('json')
    def index(self):
        # Should probably return the status of the service
        return dict()

    runs = RunsController()
    errors = ErrorsController()
