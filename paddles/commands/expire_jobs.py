from datetime import timedelta

from sqlalchemy import select

from paddles.commands import SessionCommand
from paddles.models import Job
from paddles.util import utcnow


class ExpireJobsCommand(SessionCommand):
    """
    Mark stale jobs as 'dead'

    A stale job, in this context, is a 'running' job that has not been updated
    within a certain amount of time (usually a short interval like 30m) or a
    'queued' job that has not been updated in a different amount of time
    (usually a longer interval like 14d)
    """

    arguments = SessionCommand.arguments + (
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
        super().run(args)
        self.running_delta = timedelta(minutes=int(args.running))
        self.queued_delta = timedelta(days=int(args.queued))
        self.expire_running()
        self.expire_queued()
        self.commit()

    def _do_expire(self, query, reason):
        jobs = self.session.scalars(query).all()
        print("Expiring {count} {reason} jobs".format(count=len(jobs), reason=reason))
        runs = set()
        for job in jobs:
            job.status = 'dead'
            runs.add(job.run)
        for run in runs:
            run.set_status()

    def expire_running(self):
        now = utcnow()
        query = (
            select(Job)
            .where(Job.status.in_(['running', 'waiting', 'unknown']))
            .where(~Job.updated.between(now - self.running_delta, now))
        )
        self._do_expire(query, 'running')

    def expire_queued(self):
        now = utcnow()
        query = (
            select(Job)
            .where(Job.status == 'queued')
            .where(~Job.updated.between(now - self.queued_delta, now))
        )
        self._do_expire(query, 'queued')
