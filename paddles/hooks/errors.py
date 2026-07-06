import logging
from os import path

from pecan import redirect, request
from pecan.hooks import PecanHook
from webob import exc
from webob.response import Response as WebObResponse

from paddles.exceptions import PaddlesError

log = logging.getLogger(__name__)


def json_error_response(status_int, message):
    return WebObResponse(
        json_body={"message": message},
        content_type="application/json",
        status=status_int,
    )


def redirect_error(exc: PaddlesError):
    msg = str(exc) or getattr(exc, "message", None)
    url = exc.url
    if msg:
        request.context["error_message"] = msg
        url = path.join(url, "?error_message=%s" % msg)
    redirect(url, internal=True)


def _http_exception_message(error):
    if error.detail:
        return str(error.detail)
    if error.title:
        return str(error.title)
    return "request failed"


class PaddlesErrorHook(PecanHook):
    def on_error(self, state, e):
        if isinstance(e, PaddlesError):
            redirect_error(e)
            return

        if isinstance(e, exc.HTTPException):
            return json_error_response(e.status_int, _http_exception_message(e))

        log.exception("Unhandled error")
        return json_error_response(500, "internal server error")
