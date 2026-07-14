from pecan import make_app

from .db import get_engine
from .hooks.errors import PaddlesErrorHook
from .hooks.session import SessionHook


def setup_app(config):
    app_conf = dict(config.app)
    engine = get_engine(config.sqlalchemy.url)
    hooks = [SessionHook(engine), PaddlesErrorHook()] + app_conf.pop("hooks", [])

    return make_app(
        app_conf.pop("root"),
        logging=getattr(config, "logging", {}),
        hooks=hooks,
        **app_conf
    )
