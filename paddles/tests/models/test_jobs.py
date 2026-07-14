from datetime import datetime
from sqlalchemy import select

from paddles.models.jobs import Job
from paddles.models.nodes import Node
from paddles.models.runs import Run
from paddles.util import local_datetime_to_utc


class TestJobModel:
    def test_basic_creation(self, session_factory, job_conf, uuid):
        name = str(uuid)
        new_run = Run(name)
        new_job = Job(job_conf, new_run)
        with session_factory() as session:
            session.add_all([new_run, new_job])
            assert session.scalars(select(Run).filter_by(name=name)).one().jobs == [
                new_job
            ]

    def test_basic_deletion(self, session, job_conf, name):
        new_run = Run(name)
        new_job = Job(job_conf, new_run)
        session.add(new_job)
        query = select(Job).filter(Job.run == new_run)
        assert session.scalars(query).one()
        session.delete(new_job)
        assert not session.scalars(query).first()

    def test_relationship_works(self, session, job_conf, name):
        new_run = Run(name)
        new_job = Job(job_conf, new_run)
        session.add_all([new_run, new_job])
        session.flush()
        new_job = session.get(Job, new_job.id)
        assert new_job is not None
        assert new_job.run.name == name

    def test_job_updated(self, session, job_conf, name):
        new_run = Run(name)
        new_job = Job(job_conf, new_run)
        session.add_all([new_run, new_job])
        session.flush()
        new_job = session.get(Job, new_job.id)
        assert new_job is not None
        assert isinstance(new_job.updated, datetime)

    def test_job_creates_node(self, session, job_conf, name):
        node_name = f"node.{name}"
        targets = {"foo@" + node_name: ""}
        new_run = Run(name)
        session.add_all(
            [
                new_run,
                Job(
                    job_conf
                    | {
                        "job_id": 1,
                        "name": name,
                        "targets": targets,
                    },
                    new_run,
                ),
            ]
        )
        session.flush()
        node = session.scalars(select(Node).filter_by(name=node_name)).one()
        assert node is not None
        assert node.name == node_name
        assert node.jobs[0].job_id == 1
        assert node.jobs[0].name == name

    def test_job_creates_many_nodes(self, session, job_conf, name):
        node_names = [name + f"_node{i}" for i in range(2)]
        targets = {f"foo@{name}": "" for name in node_names}
        new_run = Run(name)
        job_data = job_conf
        job_data.update(targets=targets)
        with session.no_autoflush:
            new_job = Job(job_data, new_run)
        session.add_all([new_run, new_job])
        assert set(session.scalars(select(Node.name)).all()).issuperset(set(node_names))

    def test_job_adds_node(self, session, job_conf, name):
        node_name = f"node_{name}"
        node_query = select(Node).where(Node.name == node_name)
        assert session.scalars(node_query).all() == []
        new_node = Node(name=node_name)
        session.add(new_node)
        session.flush()
        targets = {f"foo@{node_name}": ""}
        new_run = Run(name)
        job_data = job_conf
        job_data.update(targets=targets)
        new_job = Job(job_data, new_run)
        session.add_all([new_run, new_job])
        session.flush()
        found_node = session.scalars(node_query).one()
        assert found_node
        found_job = session.scalars(
            select(Job).filter(Job.target_nodes.contains(found_node))
        ).one()
        assert found_job == new_job

    def test_force_updated_time(self, session, job_conf, name):
        run = Run(name)
        time_stamp = "2014-03-31 21:25:43"
        job_data = job_conf
        job_data.update(updated=time_stamp)
        session.add(Job(job_data, run))
        local_dt = datetime.fromisoformat(time_stamp)
        utc_dt = local_datetime_to_utc(local_dt)
        job = session.scalars(select(Run).where(Run.name == run.name)).one().jobs[0]
        assert str(job.updated) == str(utc_dt)

    def test_success_updates_status(self, name):
        run = Run(name)
        job_id = "27"
        job = Job(
            dict(name=name, job_id=job_id, id=int(job_id), status="running"), run
        )
        job.update(dict(success=True))
        assert job.status == "pass"

    def test_status_dead_ignored_when_success_true(self, name):
        run = Run(name)
        job = Job(
            dict(name=name, status="running"), run
        )
        job.update(dict(success=True))
        job.update(dict(status="dead"))
        assert job.status == "pass"

    def test_job_not_started(self, name):
        run = Run(name)
        job = Job(
            dict(name=name, status="queued"), run
        )
        assert job.started is None

    def test_job_started_running(self, name):
        run = Run(name)
        job = Job(
            dict(name=name, status="running"), run
        )
        assert job.started is not None

    def test_job_started_queued(self, name):
        run = Run(name)
        job = Job(
            dict(name=name, status="queued"), run
        )
        job.update(dict(status="running"))
        assert job.started is not None

    def test_first_job_started_updates_run(self, job_conf, name):
        run = Run(name)
        job_data = job_conf
        job_data.update(status="queued")
        job = Job(job_data, run)
        job.update(dict(status="running"))
        assert run.status == "running"
        assert run.started is not None

    def test_delete_empties_run(self, session, job_conf, name):
        new_run = Run(name)
        job_data = job_conf
        new_job = Job(job_data | {"status": "queued"}, new_run)
        session.add_all([new_run, new_job])
        session.flush()
        assert new_run.status == "queued"
        assert len(new_run.jobs) == 1
        session.delete(new_job)
        session.flush()
        session.expire(new_run, ["jobs"])
        assert new_run.jobs == []
        assert new_run.status == "empty"
        new_run_copy = session.scalars(
            select(Run).where(Run.name == new_run.name)
        ).one()
        assert new_run_copy.status == "empty"

    def test_run_suite_gets_corrected(self):
        name = "teuthology-2014-05-01_07:54:18-new-suite-name:new-subsuite:new-subsub-new-branch-testing-basic-plana"  # noqa
        suite_name = "new-suite-name:new-subsuite:new-subsub"
        branch_name = "new-branch"
        new_run = Run(name)
        Job(dict(suite=suite_name, branch=branch_name), new_run)
        assert new_run.suite == suite_name
        assert new_run.branch == branch_name

    def test_run_multi_machine_type(self):
        name = "teuthology-2014-10-06_19:30:01-upgrade:dumpling-firefly-x:stress-split-giant-distro-basic-multi"
        new_run = Run(name)
        machine_type = "plana,mira,burnupi"
        Job(dict(machine_type=machine_type), new_run)
        assert new_run.machine_type == machine_type
