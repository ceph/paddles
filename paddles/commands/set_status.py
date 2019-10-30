from __future__ import print_function
from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Job, Run


def out(string):
    print("==> %s" % string)


class SetStatusCommand(BaseCommand):
    """
    Corrects Run.status
    """

    def run(self, args):
        super(SetStatusCommand, self).run(args)
        out("LOADING ENVIRONMENT")
        self.load_app()
        models.start()
        try:
            out("SETTING RUN STATUSES...")
            running = Run.query.filter(Run.status == 'running')
            to_fix = []
            for run in running:
                if run.jobs.filter(Job.status == 'running').count() == 0:
                    to_fix.append(run)
                    self._set_run_status(run)
            print("")
            out("Updated {count} runs...".format(count=len(to_fix)))
        except:
            models.rollback()
            out("ROLLING BACK...")
            raise
        else:
            out("COMMITTING...")
            models.commit()

    def _set_run_status(self, run):
        run.set_status()
        print("."),
