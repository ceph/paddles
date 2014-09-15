from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Job

from datetime import datetime, timedelta


class ExpireJobsCommand(BaseCommand):
    """
    Mark stale jobs as 'dead'
    """
    def run(self, args):
        super(ExpireJobsCommand, self).run(args)
        self.load_app()
        models.start()
        delta = timedelta(seconds=60*60*6)
        now = datetime.utcnow()
        running = Job.query.filter(Job.status == 'running')
        to_expire = running.filter(~Job.updated.between(now - delta, now))
        msg = "Expiring {count} jobs".format(count=to_expire.count())
        print msg
        for job in to_expire:
            job.status = 'dead'
        try:
            models.commit()
        except:
            print "Rolling back"
            models.rollback()
            raise
