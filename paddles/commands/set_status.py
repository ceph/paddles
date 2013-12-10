from pecan.commands.base import BaseCommand
from time import sleep

from paddles import models
from paddles.models import Job


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
        try:
            out("STARTING A TRANSACTION...")
            models.start()
            jobs = Job.query.filter(Job.status.is_(None))
            out("Updating {count} jobs...".format(count=jobs.count()))
            for job in jobs.yield_per(5):
                self._set_status(job)
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

    def _set_status(self, job):
        success = job.success
        if success is None:
            job.status = 'unknown'
        elif success is False:
            job.status = 'fail'
        elif success is True:
            job.status = 'pass'
        print ".",
