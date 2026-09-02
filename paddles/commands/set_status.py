from sqlalchemy import select

from paddles.commands import SessionCommand
from paddles.models import Run


def out(string):
    print("==> %s" % string)


class SetStatusCommand(SessionCommand):
    """
    Corrects Run.status
    """

    arguments = SessionCommand.arguments + (
        dict(
            name=["-a", "--all"],
            help="Recompute the status of every run, not just 'running' ones",
            action="store_true",
            default=False,
        ),
    )

    def run(self, args):
        super().run(args)
        out("SETTING RUN STATUSES...")
        query = select(Run)
        if not args.all:
            query = query.where(Run.status == 'running')
        fixed = 0
        for run in self.session.scalars(query.execution_options(yield_per=100)):
            old_status, new_status = run.refresh_status(self.session)
            if old_status != new_status:
                fixed += 1
                print("{name}: {old} => {new}".format(name=run.name, old=old_status, new=new_status))
        out("Updated {count} runs...".format(count=fixed))
        out("COMMITTING...")
        self.commit(out)
