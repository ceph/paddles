from pecan import expose, request, response


class ErrorsController(object):

    @expose('json')
    def invalid(self, **kw):
        msg = kw.get(
            'error_message',
            'invalid request'
        )
        response.status = 400
        return dict(message=msg)

    @expose('json')
    def not_found(self, **kw):
        msg = kw.get(
            'error_message',
            'resource was not found'
        )
        response.status = 404
        return dict(message=msg)
