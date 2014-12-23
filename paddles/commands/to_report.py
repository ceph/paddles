from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Job


def out(string):
    print "==> %s" % string


class ToReportCommand(BaseCommand):
    """
    List things to fix
    """

    arguments = BaseCommand.arguments + (
        dict(
            name="status",
            help="What status to look for",
        ),
        dict(
            name="--dead",
            help="Report jobs as dead?",
            required=False,
        ),
    )

    def run(self, args):
        super(ToReportCommand, self).run(args)
        self.load_app()
        models.start()
        query = Job.query.filter(Job.status == args.status)
        info = {}
        for job in query:
            job_ids = info.get(job.name, [])
            job_ids.append(job.job_id)
            info[job.name] = job_ids

        for (name, job_ids) in info.iteritems():
            dead = '-D ' if args.dead else ''
            cmd_str = "teuthology-report {dead} -r " + name + \
                " -j " + " -j ".join(job_ids)
            cmd_str = cmd_str.format(dead=dead)
            print cmd_str
