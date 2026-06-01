import datetime
from os import path

from pecan import redirect, request

import paddles.models
from paddles.decorators import retryOperation
from paddles.models import TEUTHOLOGY_TIMESTAMP_FMT

import logging  # isort: skip

log = logging.getLogger(__name__)

date_format = "%Y-%m-%d"


def error(url, msg=None):
    if msg:
        request.context["error_message"] = msg
        url = path.join(url, "?error_message=%s" % msg)
    redirect(url, internal=True)


@retryOperation
def create_run(name) -> paddles.models.Run:
    session = request.session
    log.info("Creating run: %s", name)
    with session.no_autoflush:
        run = paddles.models.Run(name)
        session.add(run)
        return run


def date_from_string(date_str, out_fmt=TEUTHOLOGY_TIMESTAMP_FMT, hours="00:00:00"):
    try:
        if date_str == "today":
            date = datetime.date.today()
            date_str = date.strftime(date_format)
        elif date_str == "yesterday":
            date = datetime.date.today()
            date = date.replace(day=date.day - 1)
            date_str = date.strftime(date_format)
        else:
            date = datetime.datetime.strptime(date_str, date_format)

        if out_fmt == TEUTHOLOGY_TIMESTAMP_FMT:
            date_str = "{date}_{time}".format(date=date_str, time=hours)
            date = datetime.datetime.strptime(date_str, out_fmt)

        return (date, date_str)
    except ValueError:
        error("/errors/invalid/", "date format must match %s" % date_format)
