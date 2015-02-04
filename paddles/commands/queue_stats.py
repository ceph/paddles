from pecan.commands.base import BaseCommand

from collections import OrderedDict
from datetime import date
from paddles import models
from paddles.models import Run, Job


def out(string):
    print "==> %s" % string


class QueueStatsCommand(BaseCommand):
    """
    Print the number of jobs scheduled versus completed (passed or failed) for
    each of N days in the past
    """

    arguments = BaseCommand.arguments + (dict(
        name="days",
        help="How many days to go back in history",
    ),)

    def run(self, args):
        super(QueueStatsCommand, self).run(args)
        days = int(args.days) + 1
        self.load_app()
        models.start()
        today = date.today()
        day_objs = []
        for day_num in range(days)[::-1]:
            day = date.fromordinal(today.toordinal() - day_num)
            day_objs.append(day)

        job_counts = {}
        for day in day_objs:
            if day_objs[0] == day:
                continue
            prev_day = day_objs[day_objs.index(day) - 1]
            jobs_sched = self.jobs_scheduled_between(prev_day, day).count()
            jobs_done = self.jobs_completed_between(prev_day, day).count()
            percent = float(jobs_done) / float(jobs_sched) * 100
            job_counts[day] = OrderedDict(scheduled=jobs_sched,
                                          completed=jobs_done,
                                          percent=percent,
                                          )
            print "{day}: {sched: >4} scheduled, {done: >4} completed ({percent:.0f}%)".format(
                day=day,
                sched=jobs_sched,
                done=jobs_done,
                percent=percent,
            )

    def jobs_scheduled_between(self, day1, day2):
        query = Run.query.filter(Run.scheduled.between(day1, day2))
        query = query.join(Job)
        return query

    def jobs_completed_between(self, day1, day2):
        statuses = ['pass', 'fail']
        query = self.jobs_scheduled_between(day1, day2)
        query = query.filter(Job.status.in_(statuses))
        return query


