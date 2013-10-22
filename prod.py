import os
from pecan.hooks import TransactionHook, RequestViewerHook
from paddles import models


# Server Specific Configurations
server = {
    'port': '8080',
    'host': '0.0.0.0'
}

address = 'http://paddles.sepia.font.ceph.com'

default_latest_runs_count = 20
timestamp_format = '%Y-%m-%d_%H:%M:%S'
timestamp_regex = '[0-9]{1,4}-[0-9]{1,2}-[0-9]{1,2}_[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}'  # noqa

# Pecan Application Configurations
app = {
    'root': 'paddles.controllers.root.RootController',
    'modules': ['paddles'],
    'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/paddles/templates',
    'default_renderer': 'json',
    'debug': True,
    'hooks': [
        TransactionHook(
            models.start,
            models.start_read_only,
            models.commit,
            models.rollback,
            models.clear
        ),
        RequestViewerHook(),
    ],
}

logging = {
    'loggers': {
        'root': {'level': 'INFO', 'handlers': ['console']},
        'paddles': {'level': 'DEBUG', 'handlers': ['console']},
        'py.warnings': {'handlers': ['console']},
        '__force_dict__': True
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': ('%(asctime)s %(levelname)-5.5s [%(name)s]'
                       '[%(threadName)s] %(message)s')
        }
    }
}


sqlalchemy = {
    'url': 'postgresql+psycopg2://paddles:%s@localhost/paddles' % os.environ['PADDLES_DBPASS'],
    'echo'          : True,
    'echo_pool'     : True,
    'pool_recycle'  : 3600,
    'encoding'      : 'utf-8'
}
