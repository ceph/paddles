from sqlalchemy import select

from paddles.commands import SessionCommand
from paddles.models import Run
from paddles.util import local_datetime_to_utc


def out(string):
    print("==> %s" % string)


class ReparseCommand(SessionCommand):
    """
    Reparse the name of the run and populate its fields based on the result
    """

    def run(self, args):
        super().run(args)
        for run in self.session.scalars(select(Run).execution_options(yield_per=100)):
            self._reparse(run)
        out("COMMITING... ")
        self.commit(out)

    def _reparse(self, run):
        old_values = dict(
            user=run.user,
            scheduled=run.scheduled,
            suite=run.suite,
            branch=run.branch,
            machine_type=run.machine_type,
        )
        parsed_name = run.parse_name()
        user = parsed_name.get('user', '')
        scheduled_local = parsed_name.get('scheduled', run.posted)
        scheduled = local_datetime_to_utc(scheduled_local)
        suite = parsed_name.get('suite', '')
        branch = parsed_name.get('branch', '')
        machine_type = parsed_name.get('machine_type', '')
        new_values = dict(
            user=user,
            scheduled=scheduled,
            suite=suite,
            branch=branch,
            machine_type=machine_type
        )

        if old_values != new_values:
            print("{name}".format(name=run.name), end="")
            for field in old_values.keys():
                new_value = new_values[field]
                if old_values[field] != new_value:
                    print(" | {old} => {new}".format(
                        old=old_values[field], new=new_value), end="")
                    setattr(run, field, new_value)
            print()
