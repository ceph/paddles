from sqlalchemy import func, select

from paddles.commands import SessionCommand
from paddles.models import Job, Node


def out(string):
    print("==> %s" % string)


class SetTargetsCommand(SessionCommand):
    """
    Fill in Job.target_nodes based on Job.targets
    """

    def run(self, args):
        super().run(args)
        query = select(Job).where(~Job.target_nodes.any()).where(Job.targets.isnot(None))
        count = self.session.scalar(select(func.count()).select_from(query.subquery()))
        n = 0
        for job in self.session.scalars(query.execution_options(yield_per=10)):
            n += 1
            print("Processing Job {n}/{t}\r".format(n=n, t=count), end="")
            self._populate(job)
        print()

        nodes = self.session.scalars(select(Node).where(Node.machine_type == '')).all()
        for node in nodes:
            node.machine_type = self.parse_machine_type(node.name) or ''
        self.commit(out)

    def _populate(self, job):
        if not job.targets:
            return

        for key in job.targets.keys():
            name = key.split('@')[-1]
            mtype = self.parse_machine_type(name)
            node = self.session.scalars(select(Node).where(Node.name == name)).first()
            if node is None:
                node = Node(name=name, machine_type=mtype or '')
                self.session.add(node)
            elif mtype:
                node.machine_type = mtype
            if node not in job.target_nodes:
                job.target_nodes.append(node)
        self.session.flush()

    @staticmethod
    def parse_machine_type(node_name):
        types = 'plana', 'mira', 'vps', 'burnupi', 'tala', 'saya', 'dubia', 'smithi'
        if node_name.startswith('vpm') and 'vps' in types:
            return 'vps'
        for mtype in types:
            if node_name.startswith(mtype):
                return mtype
