from pecan import expose, redirect
from webob.exc import status_map

from paddles.controllers.runs import RunsController


class RootController(object):

    @expose()
    def index(self):
        # Should probably return the status of the service
        return dict()

    runs = RunsController()
