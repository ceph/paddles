from pecan import expose

from paddles.controllers.runs import RunsController


class RootController(object):

    @expose('json')
    def index(self):
        # Should probably return the status of the service
        return dict()

    runs = RunsController()
