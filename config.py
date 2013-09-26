# Server Specific Configurations
server = {
    'port': '8080',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
app = {
    'root': 'paddles.controllers.root.RootController',
    'modules': ['paddles'],
    'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/paddles/templates',
    'default_renderer': 'json',
    'debug': True,
    'errors': {
        404: '/error/404',
        '__force_dict__': True
    }
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
    'url': 'sqlite:///dev.db',
    'echo'          : True,
    'echo_pool'     : True,
    'pool_recycle'  : 3600,
    'encoding'      : 'utf-8'
}
