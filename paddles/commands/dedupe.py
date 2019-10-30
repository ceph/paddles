from __future__ import print_function
from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Run, Job


def out(string):
    print("==> %s" % string)


class DedupeCommand(BaseCommand):
    """
    Fix runs with duplicate names
    """

    arguments = BaseCommand.arguments + (dict(
        name="pattern",
        help="The pattern to use to match run names for deduping. Use '%%' to match all runs.",  # noqa
    ),)

    def run(self, args):
        super(DedupeCommand, self).run(args)
        out("LOADING ENVIRONMENT")
        self.load_app()
        try:
            out("STARTING A TRANSACTION...")
            models.start()
            query = Run.query.filter(Run.name.like(args.pattern))
            names = [val[0] for val in query.values(Run.name)]
            out("Found {count} runs to process".format(count=len(names)))
            for name in names:
                self._fix_dupe_runs(name)
                self._fix_dupe_jobs(name)
        except:
            models.rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            models.commit()

    def _fix_dupe_runs(self, name):
        # Handles duplicate runs
        runs = Run.query.filter_by(name=name).all()
        if len(runs) <= 1:
            return

        print("{name} has {count} duplicate runs".format(
            name=name,
            count=len(runs),
        ))

        primary_run = runs[0]

        for run in runs[1:]:
            for job in run.jobs.all():
                job.run = primary_run
            run.delete()

    def _fix_dupe_jobs(self, name):
        # Handles duplicate jobs
        run = Run.query.filter_by(name=name).one()
        job_ids = sorted([val[0] for val in run.jobs.values(Job.job_id)])
        # Check if we have duplicate jobs
        unique_ids = sorted(list(set(job_ids)))
        if job_ids == unique_ids:
            return
        print("{name} has {count} duplicate jobs".format(
            name=name,
            count=(len(job_ids) - len(unique_ids)),
        ))
        for job_id in unique_ids:
            jobs = run.jobs.filter(Job.job_id == job_id).all()
            if len(jobs) == 1:
                continue
            primary_job = jobs[0]
            for job in jobs[1:]:
                primary_job.set_or_update(job.__json__())
                job.delete()
