from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Job

from datetime import datetime, timedelta


class ExpireJobsCommand(BaseCommand):
    """
    Mark stale jobs as 'dead'
    """
    running_delta = timedelta(seconds=60*60*0.5)
    queued_delta = timedelta(days=14)

    def run(self, args):
        super(ExpireJobsCommand, self).run(args)
        self.load_app()
        models.start()
        self.expire_running()
        self.expire_queued()
        self.commit()

    def _do_expire(self, query, reason):
        msg = "Expiring {count} {reason} jobs".format(
            count=query.count(),
            reason=reason,
        )
        print msg
        runs = set()
        for job in query:
            job.status = 'dead'
            runs.add(job.run)
        for run in runs:
            run.set_status()

    def expire_running(self):
        delta = self.running_delta
        now = datetime.utcnow()
        running = Job.query.filter(Job.status.in_(['running', 'waiting']))
        to_expire = running.filter(~Job.updated.between(now - delta, now))
        self._do_expire(to_expire, 'running')

    def expire_queued(self):
        delta = self.queued_delta
        now = datetime.utcnow()
        queued = Job.query.filter(Job.status == 'queued')
        to_expire = queued.filter(~Job.updated.between(now - delta, now))
        self._do_expire(to_expire, 'queued')

    def commit(self):
        try:
            models.commit()
        except:
            print "Rolling back"
            models.rollback()
            raise
