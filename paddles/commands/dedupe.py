from pecan.commands.base import BaseCommand
from pecan import conf

from paddles import models
from paddles.models import Run


def out(string):
    print "==> %s" % string


class DedupeCommand(BaseCommand):
    """
    Fix runs with duplicate names
    """

    def run(self, args):
        super(DedupeCommand, self).run(args)
        out("LOADING ENVIRONMENT")
        self.load_app()
        try:
            out("STARTING A TRANSACTION...")
            models.start()
            names = Run.query.values(Run.name)
            for name in names:
                name = name[0]  # query.values() returns a tuple, oddly
                self._fix_dupes(name)
        except:
            models.rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            models.commit()

    def _fix_dupes(self, name):
        runs = Run.query.filter_by(name=name).all()
        if len(runs) <= 1:
            return

        print "{name} has {count} dupes".format(
            name=name,
            count=len(runs),
        )

        primary_run = runs[0]

        for run in runs[1:]:
            for job in run.jobs.all():
                job.run = primary_run
            run.delete()
