from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Run


def out(string):
    print "==> %s" % string


class DeleteCommand(BaseCommand):
    """
    Delete a run
    """

    arguments = BaseCommand.arguments + (dict(
        name="name",
        help="The name of the run to delete",
    ),)

    def run(self, args):
        super(DeleteCommand, self).run(args)
        out("LOADING ENVIRONMENT")
        self.load_app()
        try:
            out("STARTING A TRANSACTION...")
            models.start()
            query = Run.query.filter(Run.name == args.name)
            run = query.one()
            out("Deleting run named %s" % run.name)
            run.delete()
        except:
            models.rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            models.commit()
