import os
from pecan.deploy import deploy


def config_file(file_name=None):
    file_name = file_name or 'config.py'
    _file = os.path.abspath(__file__)
    dirname = lambda x: os.path.dirname(x)
    parent_dir = dirname(dirname(_file))
    return os.path.join(parent_dir, file_name)


def application(environ, start_response):
    wsgi_app = deploy(config_file('local.py'))
    return wsgi_app(environ, start_response)

