from __future__ import print_function
from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Job

from datetime import datetime, timedelta


class ExpireJobsCommand(BaseCommand):
    """
    Mark stale jobs as 'dead'

    A stale job, in this context, is a 'running' job that has not been updated
    within a certain amount of time (usually a short interval like 30m) or a
    'queued' job that has not been updated in a different amount of time
    (usually a longer interval like 14d)
    """

    arguments = BaseCommand.arguments + (
        dict(
            name=["-r", "--running"],
            help="How recently-updated (in minutes) a running job should be" +
                 " to not be marked 'dead' (default: 30)",
            default=30,
        ),
        dict(
            name=["-q", "--queued"],
            help="How recently-updated (in days) a queued job should be" +
                 " to not be marked 'dead' (default: 14)",
            default=14,
        ),
    )

    def run(self, args):
        super(ExpireJobsCommand, self).run(args)
        self.running_minutes = int(args.running)
        self.running_delta = timedelta(minutes=self.running_minutes)
        self.queued_days = int(args.queued)
        self.queued_delta = timedelta(days=self.queued_days)
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
        print(msg)
        runs = set()
        for job in query:
            job.status = 'dead'
            runs.add(job.run)
        for run in runs:
            run.set_status()

    def expire_running(self):
        delta = self.running_delta
        now = datetime.utcnow()
        running = Job.query.filter(Job.status.in_(['running', 'waiting', 'unknown']))
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
            print("Rolling back")
            models.rollback()
            raise
