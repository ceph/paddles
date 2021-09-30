from __future__ import print_function
import os
import sys

from pecan.commands.base import BaseCommand


class GetSecretCommand(BaseCommand):
    """
    Get the sqlalchemy URL
    """

    secret_file = "/run/secrets/paddles_sqlalchemy_url"

    def run(self, args):
        super(GetSecretCommand, self).run(args)
        if os.path.exists(self.secret_file):
            with open(self.secret_file) as f:
                secret = f.read().strip()
        else:
            secret = os.environ.get(
                "PADDLES_SQLALCHEMY_URL", "sqlite:///dev.db")
        sys.stdout.write(secret)
