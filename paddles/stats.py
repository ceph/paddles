import logging
import statsd

from pecan import conf

log = logging.getLogger(__name__)


def get_client():
    try:
        host = conf.statsd.host
        port = conf.statsd.get("port", statsd.Connection.default_port)
        prefix = conf.statsd.prefix
        statsd.Connection.set_defaults(
            host=host,
            port=port,
        )
    except AttributeError as exc:
        log.info(
            "Could not find statsd configuration; disabling statsd. "
            "Error message was: %s" % exc.message
        )
        prefix = None
        statsd.Connection.set_defaults(
            disabled=True,
        )
    return statsd.Client(prefix)
