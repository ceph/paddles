import pytz
import tzlocal
from sqlalchemy import select

from paddles.models import Job, Run


class TestRunModel:
    def test_jobs_count(self, job_conf, session, name):
        new_run = Run(name)
        session.add_all(
            [
                Job(job_conf | {"job_id": 1}, new_run),
                Job(job_conf | {"job_id": 2}, new_run),
            ]
        )
        session.flush()
        run = session.get(Run, new_run.id)
        assert run is not None
        run_as_json = run.__json__()
        assert run_as_json["jobs_count"] == 2

    def test_run_deletion(self, job_conf, session, name):
        new_run = Run(name)
        session.add_all(
            [
                new_run,
                Job(job_conf | {"job_id": 1}, new_run),
                Job(job_conf | {"job_id": 2}, new_run),
            ]
        )
        session.flush()
        session.delete(new_run)
        session.flush()
        assert session.scalars(select(Run).filter_by(name=name)).first() is None

    def test_empty_run_deletion(self, session, name):
        new_run = Run(name)
        session.add(new_run)
        session.flush()
        session.delete(new_run)
        session.flush()
        assert session.scalars(select(Run).filter_by(name=name)).first() is None

    def test_job_deletion(self, job_conf, session, name):
        new_run = Run(name)
        session.add_all(
            [
                new_run,
                Job(job_conf | {"job_id": 1}, new_run),
            ]
        )
        session.flush()
        session.delete(new_run)
        session.flush()
        assert not session.scalars(select(Run).filter_by(name=name)).first()

    def test_scheduled(self, session):
        name = "teuthology-2013-10-23_01:35:02-upgrade-small-next-testing-basic-vps"  # noqa
        new_run = Run(name)
        session.add(new_run)
        scheduled_aware = pytz.utc.localize(new_run.scheduled)
        localtz = tzlocal.get_localzone()
        scheduled_local = scheduled_aware.astimezone(localtz)
        scheduled_local_naive = scheduled_local.replace(tzinfo=None)
        assert str(scheduled_local_naive) == "2013-10-23 01:35:02"

    def test_updated(self, job_conf, session, name):
        new_run = Run(name)
        session.add(new_run)
        for i in range(1, 5):
            session.add(Job(job_conf | {"job_id": 60 + i}, new_run))
        session.flush()
        new_run = session.scalars(select(Run).filter_by(name=name)).first()
        assert new_run is not None
        assert new_run.updated == new_run.get_jobs()[-1].updated

    def test_run_suite_typical(self):
        name = "teuthology-2013-10-22_03:00:02-big-next-testing-basic-plana"
        new_run = Run(name)
        assert new_run.suite == "big"

    def test_run_suite_hyphenated(self):
        name = "teuthology-2013-10-22_03:00:02-ceph-deploy-next-testing-basic-plana"  # noqa
        new_run = Run(name)
        assert new_run.suite == "ceph-deploy"

    def test_run_suite_weird(self):
        name = "teuthology-2013-10-23_00:30:38-rgw-next---basic-saya"
        new_run = Run(name)
        assert new_run.suite == "rgw"

    def test_run_suite_unlisted(self):
        name = "teuthology-2013-10-22_03:00:02-kittens-next-testing-basic-plana"
        new_run = Run(name)
        assert new_run.suite == "kittens"

    def test_run_suite_nosuite(self, name):
        new_run = Run(name)
        assert new_run.suite == ""

    def test_run_branch(self):
        name = "teuthology-2013-10-22_03:00:02-big-next-testing-basic-plana"
        new_run = Run(name)
        assert new_run.branch == "next"

    def test_run_branch_hyphenated(self):
        name = "teuthology-2013-10-22_03:00:02-big-wip-9999-testing-basic-plana"
        new_run = Run(name)
        assert new_run.branch == "wip-9999"

    def test_run_hyphenated_suite_and_branch(self):
        name = (
            "teuthology-2013-10-22_03:00:02-ceph-deploy-wip-9999-testing-basic-plana"  # noqa
        )
        new_run = Run(name)
        assert (new_run.suite, new_run.branch) == ("ceph-deploy", "wip-9999")

    def test_run_status_empty(self, name):
        new_run = Run(name)
        assert new_run.status == "empty"

    def test_run_status_running(self, job_conf, name):
        new_run = Run(name)
        Job(job_conf | {"status": "running"}, new_run)
        Job(job_conf | {"status": "pass"}, new_run)
        assert new_run.status == "running"

    def test_run_status_queued(self, name):
        new_run = Run(name)
        Job(dict(job_id=9, id=9, status="queued"), new_run)
        Job(dict(job_id=10, id=10, status="queued"), new_run)
        assert new_run.status == "queued"

    def test_run_status_queued_to_running(self, name):
        new_run = Run(name)
        job = Job(dict(job_id=11, id=11, status="queued"), new_run)
        Job(dict(job_id=12, id=12, status="queued"), new_run)
        job.update(dict(status="running"))
        assert new_run.status == "running"

    def test_run_status_running_to_dead(self, name):
        new_run = Run(name)
        jobs = []
        job_count = 5
        for i in range(job_count):
            jobs.append(Job(dict(job_id=20 + i, id=20 + i, status="running"), new_run))
        for job in jobs:
            job.update(dict(status="dead"))
        assert new_run.status == "finished dead"

    def test_run_status_dead_to_running(self, name):
        new_run = Run(name)
        jobs = []
        job_count = 5
        for i in range(job_count):
            jobs.append(Job(dict(job_id=30 + i, id=30 + i, status="dead"), new_run))
        for job in jobs:
            job.update(dict(status="running"))
        assert new_run.status == "running"

    def test_run_status_fail(self, name):
        new_run = Run(name)
        Job(dict(job_id=13, id=13, status="fail"), new_run)
        assert new_run.status == "finished fail"

    def test_run_status_pass(self, name):
        new_run = Run(name)
        Job(dict(job_id=14, id=14, status="pass"), new_run)
        assert new_run.status == "finished pass"

    def test_run_status_one_dead(self, name):
        new_run = Run(name)
        Job(dict(job_id=15, id=15, status="dead"), new_run)
        Job(dict(job_id=50, id=50, status="pass"), new_run)
        assert new_run.status == "finished fail"

    def test_run_status_all_dead(self, name):
        new_run = Run(name)
        Job(dict(job_id=16, id=16, status="dead"), new_run)
        assert new_run.status == "finished dead"

    def test_run_status_one_pass(self, name):
        new_run = Run(name)
        Job(dict(job_id=15, id=15, status="queued"), new_run)
        Job(dict(job_id=50, id=50, status="pass"), new_run)
        assert new_run.status == "queued"

    def test_status_sql_matches_python_property(self, session, name):
        run = Run(name)
        session.add(run)
        session.flush()
        session.add_all(
            [
                Job({"job_id": "1", "status": "queued"}, run),
                Job({"job_id": "2", "status": "queued"}, run),
            ]
        )
        session.flush()
        session.refresh(run)

        assert run.status == "queued"
        assert run in session.scalars(select(Run).where(Run.status == "queued")).all()
        assert run not in session.scalars(select(Run).where(Run.status == "running")).all()

    def test_run_href_serializes_as_string(self, session, name):
        run = Run(name)
        session.add(run)
        session.flush()

        assert isinstance(run.href, str)
        assert isinstance(run.__json__()["href"], str)

    def test_run_user(self):
        name = "teuthology-2013-12-22_01:00:02-x-x-x-x-x"
        new_run = Run(name)
        assert new_run.user == "teuthology"

    def test_run_machine_type(self):
        name = "x-2013-12-22_01:00:02-big-x-x-x-plana"
        new_run = Run(name)
        assert new_run.machine_type == "plana"

    def test_run_results(self, name):
        new_run = Run(name)
        stats_in = {
            "pass": 9,
            "fail": 1,
            "dead": 6,
            "running": 5,
            "sha1": None,
            "waiting": 1,
            "unknown": 1,
            "queued": 1,
            "flavor": None,
        }
        statuses = stats_in.keys()
        stats_in["total"] = sum(_ for _ in stats_in.values() if _)
        stats_out = {}
        for i in range(stats_in["total"]):
            for status in statuses:
                count = stats_out.get(status, 0)
                count += 1
                # treat None as 0
                if count <= (stats_in[status] or 0):
                    break
            Job(dict(job_id=70 + i, id=int(70 + i), status=status), new_run)
            stats_out[status] = count
        assert new_run.results == stats_in

    def test_run_priority(self, name):
        new_run = Run(name)
        Job(dict(job_id=1, id=1, status="queued", priority=99), new_run)
        assert new_run.priority == 99

    def test_run_flavor(self, name):
        new_run = Run(name)
        Job(dict(job_id=1, id=1, status="queued", flavor="blah"), new_run)
        run_result = new_run.results
        assert run_result.get("flavor") == "blah"
