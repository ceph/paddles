from pecan import expose

from paddles.controllers.runs import RunsController
from paddles.controllers.nodes import NodesController
from paddles.controllers.errors import ErrorsController
from paddles.models import Run, Job, Session
from paddles.controllers.util import last_seen


class RootController(object):

    _help = {
        "docs": "https://github.com/ceph/paddles",
        "extensions": {
            "Chrome": "https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc",
            "Firefox" : "https://addons.mozilla.org/en-US/firefox/addon/jsonview/"
        }
    }

    @expose('json')
    def index(self):

        with Session.no_autoflush:
            return dict(
                _help_=self._help,
                last_run=last_seen(Run),
                last_job=last_seen(Job),
            )

    runs = RunsController()
    errors = ErrorsController()
    nodes = NodesController()
