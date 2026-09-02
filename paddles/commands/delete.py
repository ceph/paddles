from sqlalchemy import select

from paddles.commands import SessionCommand
from paddles.models import Run


def out(string):
    print("==> %s" % string)


class DeleteCommand(SessionCommand):
    """
    Delete a run
    """

    arguments = SessionCommand.arguments + (dict(
        name="name",
        help="The name of the run to delete",
    ),)

    def run(self, args):
        super().run(args)
        run = self.session.scalars(select(Run).where(Run.name == args.name)).one()
        out("Deleting run named %s" % run.name)
        self.session.delete(run)
        out("COMMITING... ")
        self.commit(out)
