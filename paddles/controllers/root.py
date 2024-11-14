from pecan import expose

from paddles.controllers.runs import RunsController
from paddles.controllers.jobs import JobsListController
from paddles.controllers.nodes import NodesController
from paddles.controllers.errors import ErrorsController
from paddles.controllers.queue import QueuesController

class RootController(object):

    _help = {
        "repo": "https://github.com/ceph/paddles",
    }

    @expose("json")
    def index(self):
        return dict()

    runs = RunsController()
    errors = ErrorsController()
    nodes = NodesController()
    queue = QueuesController()
    jobs = JobsListController()
