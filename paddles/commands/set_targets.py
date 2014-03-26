from pecan.commands.base import BaseCommand

from paddles.models import start, rollback, commit, Job
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
            start()
            jobs = Job.query.filter(~Job.target_nodes.any()).all()
            for job in jobs:
                self._populate(job)

            nodes = Node.query.filter(Node.machine_type.is_(None)).all()
            for node in nodes:
                node.machine_type = self.parse_machine_type(node.name)
        except:
            rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            commit()

    def _populate(self, job):
        print "Job: %s/%s" % (job.name, job.job_id)
        if not job.targets:
            return

        for key in job.targets.keys():
            name = key.split('@')[1]
            mtype = self.parse_machine_type(name)
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
            if mtype:
                node.machine_type = mtype
            if node not in job.target_nodes:
                job.target_nodes.append(node)

    @staticmethod
    def parse_machine_type(node_name):
        types = Node.machine_types
        if node_name.startswith('vpm') and 'vps' in types:
            return 'vps'
        for mtype in types:
            if node_name.startswith(mtype):
                return mtype
