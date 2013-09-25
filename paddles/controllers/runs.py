from pecan import expose


class RunController(object):

    def __init__(self, _id):
        self._id = _id
        # grab this guy from DB

    @expose()
    def index(self):
        # return JSON repr of the database obj
        # with jsonify
        return dict()


class RunsController(object):

    @expose(generic=True)
    def index(self):
        return dict()

    @index.when(method='POST')
    def index_post(self):
        # save to DB here
        return dict()

    @expose()
    def _lookup(self, _id, *remainder):
        return RunController(_id), remainder

