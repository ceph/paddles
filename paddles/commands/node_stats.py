import json
from datetime import date, datetime

from sqlalchemy import select

from paddles.commands import SessionCommand
from paddles.models import Job


class NodeStatsCommand(SessionCommand):
    """
    Print JSON-formatted statistics on jobs executed in a given timeframe and
    how many nodes they used.
    """
    epoch = datetime(1970, 1, 1)

    arguments = SessionCommand.arguments + (
        dict(
            name="days",
            help="How many days to go back in history",
        ),
        dict(
            name=["-m", "--machine-type"],
            help="Only look at runs using this exact machine type",
            default=None,
        ),
    )

    def run(self, args):
        super().run(args)
        days = int(args.days) + 1
        self.machine_type = args.machine_type
        today = date.today()
        day_objs = []
        for day_num in range(days)[::-1]:
            day = date.fromordinal(today.toordinal() - day_num)
            day_objs.append(day)

        all_jobs = list()
        for day in day_objs:
            if day_objs[0] == day:
                continue
            prev_day = day_objs[day_objs.index(day) - 1]
            jobs_done = self.session.scalars(self.jobs_completed_between(prev_day, day))
            for job in jobs_done:
                if not job.started:
                    continue
                job_info = self.get_job_info(job)
                all_jobs.append(job_info)
        print(json.dumps(all_jobs, indent=2))

    def jobs_scheduled_between(self, day1, day2):
        query = select(Job).where(Job.posted.between(day1, day2))
        if self.machine_type:
            query = query.where(Job.machine_type == self.machine_type)
        return query

    def jobs_completed_between(self, day1, day2):
        statuses = ['pass', 'fail', 'dead']
        query = self.jobs_scheduled_between(day1, day2)
        query = query.where(Job.status.in_(statuses))
        return query

    def seconds_since_epoch(self, datetime_obj):
        return (datetime_obj - self.epoch).total_seconds()

    def get_job_info(self, job):
        started = self.seconds_since_epoch(job.started)
        updated = self.seconds_since_epoch(job.updated)
        duration = job.duration or 0
        runtime = updated - started
        waited = runtime - duration
        job_info = dict(
            job='/'.join((job.name, job.job_id)),
            status=job.status,
            suite=job.run.suite,
            nodes=len(job.target_nodes),
            duration=duration,
            runtime=runtime,
            waited=waited,
            description=job.description,
        )
        return job_info
