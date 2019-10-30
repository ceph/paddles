from __future__ import print_function
from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Job, Node


class NodeJobsCommand(BaseCommand):
    """
    List the last 10 jobs run on a given node
    """

    arguments = BaseCommand.arguments + (
        dict(
            name="node",
            help="The name of the node",
        ),
        dict(
            name=['-c', '--job-count'],
            help="How many jobs to display",
            default=10,
        ),
    )

    def run(self, args):
        super(NodeJobsCommand, self).run(args)
        self.load_app()
        models.start()
        node_name = args.node
        job_count = int(args.job_count)
        node_obj = Node.query.filter(Node.name.startswith(node_name)).one()
        jobs = Job.query.filter(
            Job.target_nodes.contains(node_obj)).filter(
                ~Job.updated.is_(None)).order_by(
                    Job.updated.desc()).limit(job_count)
        if not jobs.count():
            print("No jobs found for %s" % node_name)
            return
        for job in jobs:
            print('%s/%s/' % (job.run.name, job.job_id))
