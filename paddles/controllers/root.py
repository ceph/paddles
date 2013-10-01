from pecan import expose

from paddles.controllers.runs import RunsController
from paddles.controllers.errors import ErrorsController
from paddles.models import Run, Job
from paddles.controllers.util import last_seen


class RootController(object):

    @expose('json')
    def index(self):
        # Should probably return the status of the service
        return dict(
            last_run = last_seen(Run),
            last_job = last_seen(Job),
        )

    runs = RunsController()
    errors = ErrorsController()


