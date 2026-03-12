from datetime import datetime

from sqlalchemy import select

from paddles import models
from paddles.models import Job, Node, Run, Session
from paddles.tests import TestModel
from paddles.util import local_datetime_to_utc


class TestJobModel(TestModel):
    def test_basic_creation(self, job_conf):
        new_run = Run("test_basic_creation")
        Session.add(new_run)
        Session.add(
            Job(
                job_conf,
                new_run,
            )
        )
        assert Session.scalars(select(Job).filter_by(job_id="1")).first()

    def test_basic_deletion(self, job_conf):
        new_run = Run("test_basic_deletion")
        new_job = Job(job_conf, new_run)
        Session.add(new_job)
        query = select(Job).filter_by(job_id="1")
        assert Session.scalars(query).first()
        Session.delete(new_job)
        assert not Session.scalars(query).first()

    def test_relationship_works(self, job_conf):
        new_run = Run("test_relationship_works")
        new_job = Job(job_conf, new_run)
        Session.add_all([new_run, new_job])
        models.commit()
        new_job = Session.get(Job, new_job.id)
        assert new_job is not None
        assert new_job.run.name == "test_relationship_works"

    def test_job_updated(self, job_conf):
        new_run = Run("test_job_updated")
        new_job = Job(job_conf, new_run)
        Session.add_all([new_run, new_job])
        models.commit()
        new_job = Session.get(Job, new_job.id)
        assert new_job is not None
        assert isinstance(new_job.updated, datetime)

    def test_job_creates_node(self, job_conf):
        run_name = "test_job_creates_node"
        node_name = "node.name"
        targets = {"foo@" + node_name: ""}
        new_run = Run(run_name)
        Session.add_all(
            [
                new_run,
                Job(
                    job_conf
                    | {
                        "job_id": 1,
                        "name": run_name,
                        "targets": targets,
                    },
                    new_run,
                ),
            ]
        )
        node = Session.get(Node, 1)
        assert node is not None
        assert node.name == node_name
        assert node.jobs[0].job_id == 1
        assert node.jobs[0].name == run_name

    def test_job_creates_many_nodes(self, job_conf):
        run_name = "test_job_creates_many_nodes"
        node_names = ["node1.name", "node2.name", "node3.name"]
        targets = {f"foo@{name}": "" for name in node_names}
        new_run = Run(run_name)
        job_data = job_conf
        job_data.update(targets=targets)
        new_job = Job(job_data, new_run)
        Session.add_all([new_run, new_job])
        assert sorted(Session.scalars(select(Node.name)).all()) == node_names

    def test_job_adds_node(self, job_conf):
        run_name = "test_job_adds_node"
        node_name = "added_node"
        node_query = select(Node).where(Node.name == node_name)
        assert Session.scalars(node_query).all() == []
        new_node = Node(name=node_name)
        Session.add(new_node)
        targets = {f"foo@{node_name}": ""}
        new_run = Run(run_name)
        job_data = job_conf
        job_data.update(targets=targets)
        new_job = Job(job_data, new_run)
        Session.add_all([new_run, new_job])
        found_node = Session.scalars(node_query).one()
        assert found_node
        found_job = Session.scalars(
            select(Job).filter(Job.target_nodes.contains(found_node))
        ).one()
        assert found_job == new_job

    def test_force_updated_time(self, job_conf):
        run_name = "test_force_updated_time"
        run = Run(run_name)
        time_stamp = "2014-03-31 21:25:43"
        job_data = job_conf
        job_data.update(updated=time_stamp)
        Session.add(Job(job_data, run))
        local_dt = datetime.fromisoformat(time_stamp)
        utc_dt = local_datetime_to_utc(local_dt)
        job = Session.scalars(select(Run).where(Run.name == run.name)).one().jobs[0]
        assert str(job.updated) == str(utc_dt)

    def test_success_updates_status(self):
        run_name = "test_success_updates_status"
        run = Run(run_name)
        job_id = "27"
        job = Job(
            dict(name=run_name, job_id=job_id, id=int(job_id), status="running"), run
        )
        models.commit()
        job.update(dict(success=True))
        models.commit()
        assert job.status == "pass"

    def test_status_dead_ignored_when_success_true(self):
        run_name = "test_status_dead_ignored_when_success_set"
        run = Run(run_name)
        job_id = "28"
        job = Job(
            dict(name=run_name, job_id=job_id, id=int(job_id), status="running"), run
        )
        models.commit()
        job.update(dict(success=True))
        models.commit()
        job.update(dict(status="dead"))
        models.commit()
        assert job.status == "pass"

    def test_job_not_started(self):
        run_name = "test_job_not_started"
        run = Run(run_name)
        job_id = "29"
        job = Job(
            dict(name=run_name, job_id=job_id, id=int(job_id), status="queued"), run
        )
        assert job.started is None

    def test_job_started_running(self):
        run_name = "test_job_started_running"
        run = Run(run_name)
        job_id = "30"
        job = Job(
            dict(name=run_name, job_id=job_id, id=int(job_id), status="running"), run
        )
        assert job.started is not None

    def test_job_started_queued(self):
        run_name = "test_job_started_queued"
        run = Run(run_name)
        job_id = "31"
        job = Job(
            dict(name=run_name, job_id=job_id, id=int(job_id), status="queued"), run
        )
        job.update(dict(status="running"))
        assert job.started is not None

    def test_first_job_started_updates_run(self, job_conf):
        run_name = "test_first_job_started_updates_run"
        run = Run(run_name)
        job_data = job_conf
        job_data.update(status="queued")
        job = Job(job_data, run)
        Session.add(job)
        job.update(dict(status="running"))
        assert run.status == "running"
        assert run.started is not None

    def test_delete_empties_run(self, job_conf):
        new_run = Run("test_delete_empties_run")
        job_data = job_conf
        new_job = Job(job_data | {"status": "queued"}, new_run)
        Session.add_all([new_run, new_job])
        models.commit()
        assert new_run.status == "queued"
        Session.delete(new_job)
        models.commit()
        new_run_copy = Session.scalars(
            select(Run).where(Run.name == new_run.name)
        ).one()
        assert new_run_copy.status == "empty"

    def test_run_suite_gets_corrected(self):
        run_name = "teuthology-2014-05-01_07:54:18-new-suite-name:new-subsuite:new-subsub-new-branch-testing-basic-plana"  # noqa
        suite_name = "new-suite-name:new-subsuite:new-subsub"
        branch_name = "new-branch"
        new_run = Run(run_name)
        Job(dict(job_id="34", id=34, suite=suite_name, branch=branch_name), new_run)
        models.commit()
        assert new_run.suite == suite_name
        assert new_run.branch == branch_name

    def test_run_multi_machine_type(self):
        run_name = "teuthology-2014-10-06_19:30:01-upgrade:dumpling-firefly-x:stress-split-giant-distro-basic-multi"
        new_run = Run(run_name)
        machine_type = "plana,mira,burnupi"
        Job(dict(job_id=35, id=35, machine_type=machine_type), new_run)
        models.commit()
        assert new_run.machine_type == machine_type
