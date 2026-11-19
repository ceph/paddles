from collections import defaultdict

from sqlalchemy import select

from paddles.commands import SessionCommand
from paddles.models import Run


def out(string):
    print("==> %s" % string)


class DedupeCommand(SessionCommand):
    """
    Fix runs with duplicate names
    """

    arguments = SessionCommand.arguments + (dict(
        name="pattern",
        help="The pattern to use to match run names for deduping. Use '%%' to match all runs.",  # noqa
    ),)

    def run(self, args):
        super().run(args)
        query = select(Run.name).where(Run.name.like(args.pattern)).distinct()
        names = self.session.scalars(query).all()
        out("Found {count} runs to process".format(count=len(names)))
        for name in names:
            self._fix_dupe_runs(name)
            self._fix_dupe_jobs(name)
        out("COMMITING... ")
        self.commit(out)

    def _fix_dupe_runs(self, name):
        # Handles duplicate runs
        runs = self.session.scalars(select(Run).where(Run.name == name).order_by(Run.id)).all()
        if len(runs) <= 1:
            return

        print("{name} has {count} duplicate runs".format(
            name=name,
            count=len(runs),
        ))

        primary_run = runs[0]

        for run in runs[1:]:
            for job in list(run.jobs):
                job.run = primary_run
            self.session.delete(run)
        self.session.flush()

    def _fix_dupe_jobs(self, name):
        # Handles duplicate jobs
        run = self.session.scalars(select(Run).where(Run.name == name)).one()
        by_id = defaultdict(list)
        for job in run.jobs:
            by_id[job.job_id].append(job)
        dupes = {job_id: jobs for job_id, jobs in by_id.items() if len(jobs) > 1}
        if not dupes:
            return
        print("{name} has {count} duplicate jobs".format(
            name=name,
            count=sum(len(jobs) - 1 for jobs in dupes.values()),
        ))
        for job_id, jobs in dupes.items():
            jobs = sorted(jobs, key=lambda j: j.id)
            primary_job = jobs[0]
            for job in jobs[1:]:
                primary_job.update(job.__json__())
                self.session.delete(job)
        self.session.flush()
        run.refresh_status(self.session)
