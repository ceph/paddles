from pecan.commands.base import BaseCommand
from pecan import conf

from paddles import models


def out(string):
    print "==> %s" % string


class ReparseCommand(BaseCommand):
    """
    Reparse the name of the run and populate its fields based on the result
    """

    def run(self, args):
        super(ReparseCommand, self).run(args)
        out("LOADING ENVIRONMENT")
        self.load_app()
        try:
            out("STARTING A TRANSACTION...")
            models.start()
            runs = models.Run.query.all()
            for run in runs:
                self._reparse(run)
        except:
            models.rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            models.commit()

    def _reparse(self, run):
        old_values = dict(
            user=run.user,
            scheduled=run.scheduled,
            suite=run.suite,
            branch=run.branch,
            machine_type=run.machine_type,
        )
        parsed_name = run._parse_name()
        user = parsed_name.get('user', '')
        scheduled = parsed_name.get('scheduled', run.posted)
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
            print "{name}".format(name=run.name),
            for field in old_values.keys():
                new_value = new_values[field]
                if old_values[field] != new_value:
                    print "| {old} => {new}".format(
                        old=old_values[field], new=new_value),
                    setattr(run, field, new_value)
            print
