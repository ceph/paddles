from dozer import Dozer
from pecan import make_app
from paddles import models


def setup_app(config):

    models.init_model()
    app_conf = dict(config.app)

    app = make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        **app_conf
    )
    return Dozer(app)
