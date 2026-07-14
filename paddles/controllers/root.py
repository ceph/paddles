from pecan import expose

from .errors import ErrorsController
from .jobs import JobsListController
from .nodes import NodesController
from .queue import QueuesController
from .runs import RunsController


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
