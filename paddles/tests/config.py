# Server Specific Configurations
server = {
    'port': '8080',
    'host': '0.0.0.0'
}

address = 'http://localhost:%s' % server['port']
job_log_href_templ = 'http://qa-proxy.ceph.com/teuthology/{run_name}/{job_id}/teuthology.log'  # noqa

default_latest_runs_count = 20

# Pecan Application Configurations
app = {
    'root': 'paddles.controllers.root.RootController',
    'modules': ['paddles'],
    'static_root': '%(confdir)s/../../public',
    'template_path': '%(confdir)s/../templates',
    'debug': True,
    'errors': {
        '404': '/error/404',
        '__force_dict__': True
    },
}

sqlalchemy = {
    'url': 'sqlite:////tmp/test.db',
    #'url': 'postgresql+psycopg2://paddles:paddles@localhost/',
    'echo':         True,
    'echo_pool':    True,
    'pool_recycle': 3600,
    'encoding':     'utf-8'
}
