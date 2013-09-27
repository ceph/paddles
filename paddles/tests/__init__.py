import os
from pecan import set_config
from pecan.testing import load_test_app

__all__ = ['FunctionalTest']


class FunctionalTest(object):
    """
    Used for functional tests where you need to test your
    literal application and its integration with the framework.
    """

    def setup(self):
        self.app = load_test_app(os.path.join(
            os.path.dirname(__file__),
            'config.py'
        ))

    def tear_down(self):
        set_config({}, overwrite=True)
