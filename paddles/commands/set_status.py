from pecan.commands.base import BaseCommand
from time import sleep

from paddles import models
from paddles.models import Job, Run


def out(string):
    print "==> %s" % string


class SetStatusCommand(BaseCommand):
    """
    Fills in Job.status for jobs that were added before that field existed
    """

    def run(self, args):
        super(SetStatusCommand, self).run(args)
        out("LOADING ENVIRONMENT")
        self.load_app()
        models.start()
        try:
            out("SETTING JOB STATUSES...")
            jobs = Job.query.filter(Job.status.is_(None))
            out("Updating {count} jobs...".format(count=jobs.count()))
            for job in jobs.yield_per(5):
                self._set_job_status(job)
                # Be slightly polite to the db
                sleep(0.01)
            print ""
        except:
            models.rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            models.commit()

        try:
            out("SETTING RUN STATUSES...")
            runs = Run.query.filter(Run.status.is_(None))
            out("Updating {count} runs...".format(count=runs.count()))
            for run in runs.yield_per(5):
                self._set_run_status(run)
                # Be slightly polite to the db
                sleep(0.01)
            print ""
        except:
            models.rollback()
            out("ROLLING BACK...")
            raise
        else:
            out("COMMITTING...")
            models.commit()

    def _set_job_status(self, job):
        success = job.success
        if success is None:
            job.status = 'unknown'
        elif success is False:
            job.status = 'fail'
        elif success is True:
            job.status = 'pass'
        print ".",

    def _set_run_status(self, run):
        run.set_status()
        print ".",
