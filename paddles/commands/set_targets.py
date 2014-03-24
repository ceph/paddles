from pecan.commands.base import BaseCommand

from paddles import models
from paddles.models import Node


def out(string):
    print "==> %s" % string


class SetTargetsCommand(BaseCommand):
    """
    Fill in Job.target_nodes based on Job.targets
    """

    def run(self, args):
        super(SetTargetsCommand, self).run(args)
        out("LOADING ENVIRONMENT")
        self.load_app()
        try:
            out("STARTING A TRANSACTION...")
            models.start()
            jobs = models.Job.query.all()
            for job in jobs:
                self._populate(job)
        except:
            models.rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            models.commit()

    def _populate(self, job):
        print "Job: %s/%s" % (job.name, job.job_id)
        if not job.targets:
            return

        for key in job.targets.keys():
            name = key.split('@')[1]
            node_q = Node.query.filter(Node.name == name)
            print " node: exists={count}, name={name}".format(
                count=node_q.count(),
                name=name,
            )
            if node_q.count() == 0:
                print "  Creating Node with name: %s" % name
                node = Node(name=name)
            else:
                node = node_q.one()
            if node not in job.target_nodes:
                job.target_nodes.append(node)
