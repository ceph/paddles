from sqlalchemy import select

from paddles.commands import SessionCommand
from paddles.models import Job, Node


class NodeJobsCommand(SessionCommand):
    """
    List the last 10 jobs run on a given node
    """

    arguments = SessionCommand.arguments + (
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
        super().run(args)
        node_name = args.node
        job_count = int(args.job_count)
        node = self.session.scalars(
            select(Node).where(Node.name.startswith(node_name))
        ).one()
        jobs = self.session.scalars(
            select(Job)
            .where(Job.target_nodes.contains(node))
            .where(~Job.updated.is_(None))
            .order_by(Job.updated.desc())
            .limit(job_count)
        ).all()
        if not jobs:
            print("No jobs found for %s" % node_name)
            return
        for job in jobs:
            print('%s/%s/' % (job.run.name, job.job_id))
