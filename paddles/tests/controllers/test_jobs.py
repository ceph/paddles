from datetime import datetime

from sqlalchemy import select

from paddles.models import TEUTHOLOGY_TIMESTAMP_FMT, Job
from paddles.util import local_datetime_to_utc


class TestJobsController:
    def test_get_root(self, app):
        response = app.get("/")
        assert response.status_int == 200

    def test_get_some_jobs_back(self, app, job_conf):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json("/runs/foo/jobs/", job_conf)
        response = app.get("/runs/foo/jobs/")
        assert len(response.json) == 1
        assert response.json[0]["job_id"] == "1"

    def test_attempt_to_create_a_new_job(self, app, job_conf):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json("/runs/foo/jobs/", job_conf)
        response = app.post_json("/runs/foo/jobs/", dict(), expect_errors=True)
        assert response.status_code == 400

    def test_to_create_a_new_job(self, app, job_conf, session):
        app.post_json("/runs/", dict(name="foo"))
        response = app.post_json(
            "/runs/foo/jobs/", job_conf | {"status": "queued"}
        )
        assert response.status_code == 200
        assert (
            session.scalars(select(Job).where(Job.run.has(name="foo"))).one().status
            == "queued"
        )

    def test_allows_waiting_status(self, app, job_conf):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json(
            "/runs/foo/jobs/", job_conf | {"status": "waiting"}
        )
        response = app.get("/runs/foo/jobs/1/")
        job = response.json
        assert job["status"] == "waiting"

    def test_to_get_newly_created_job(self, app, job_conf):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json(
            "/runs/foo/jobs/", job_conf | {"status": "waiting"}
        )
        app.post_json(
            "/runs/foo/jobs/", job_conf | {"status": "waiting", "job_id": "2"}
        )
        response = app.get("/runs/foo/jobs/2/")
        assert response.status_code == 200

    def test_update_a_job(self, app, job_conf):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json("/runs/foo/jobs/", job_conf | {"user": "user1"})
        app.post_json(
            "/runs/foo/jobs/", job_conf | {"user": "user1", "job_id": "2"}
        )
        response = app.put_json("/runs/foo/jobs/2/", dict(user="user2"))
        assert response.status_code == 200
        response = app.get("/runs/foo/jobs/2/")
        assert response.json["user"] == "user2"

    def test_create_run_if_it_does_not_exist(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"user": "user1"})
        response = app.get("/runs/foo/jobs/1/")
        assert response.json["job_id"] == "1"

    def test_slice_valid(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf)
        response = app.get("/runs/foo/jobs/?fields=job_id")
        assert response.json == [dict(job_id="1")]

    def test_status_dead_ignored_by_completed_job(self, app, job_conf):
        app.post_json(
            "/runs/RUN/jobs/", job_conf | {"success": False, "status": "fail"}
        )
        app.put_json("/runs/RUN/jobs/1/", job_conf | {"status": "dead"})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "fail"

    def test_status_dead_not_ignored_by_running_job(self, app, job_conf):
        app.post_json("/runs/RUN/jobs/", job_conf)
        app.put_json("/runs/RUN/jobs/1/", job_conf | {"status": "dead"})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "dead"

    def test_null_success_means_status_queued(self, app, job_conf):
        app.post_json("/runs/RUN/jobs/", job_conf | {"success": None})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "queued"

    def test_success_true_means_status_pass(self, app, job_conf):
        app.post_json("/runs/RUN/jobs/", job_conf | {"success": True})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "pass"

    def test_success_false_means_status_fail(self, app, job_conf):
        app.post_json("/runs/RUN/jobs/", job_conf | {"success": False})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "fail"

    def test_status_dead_means_success_null(self, app, job_conf):
        app.post_json("/runs/RUN/jobs/", job_conf | {"status": "dead"})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("success") is None

    def test_status_dead_success_false_means_status_dead(self, app, job_conf):
        app.post_json(
            "/runs/RUN/jobs/", job_conf | {"success": False, "status": "dead"}
        )
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "dead"

    def test_status_dead_success_false_means_status_dead_repost_1(self, app, job_conf):
        app.post_json("/runs/RUN/jobs/", job_conf | {"user": "tester"})
        app.put_json("/runs/RUN/jobs/1/", {"status": "running"})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "running"
        app.put_json("/runs/RUN/jobs/1/", {"success": False, "status": "dead"})
        app.put_json("/runs/RUN/jobs/1/", {"success": False, "status": "dead"})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "dead"

    def test_status_dead_success_false_means_status_dead_repost_2(self, app, job_conf):
        app.post_json("/runs/RUN/jobs/", job_conf | {"user": "tester"})
        app.put_json("/runs/RUN/jobs/1/", {"status": "running"})
        app.put_json("/runs/RUN/jobs/1/", {"success": False, "status": "dead"})
        app.put_json("/runs/RUN/jobs/1/", {"status": "dead"})
        response = app.get("/runs/RUN/jobs/1/")
        assert response.json.get("status") == "dead"

    def test_manual_updated_time(self, app, job_conf):
        time_stamp = "2014-03-31 21:25:43"
        run_name = "manual_update"
        app.post_json("/runs/", dict(name=run_name))
        app.post_json(
            "/runs/%s/jobs/" % run_name, job_conf | {"updated": time_stamp}
        )
        local_dt = datetime.fromisoformat(time_stamp)
        utc_dt = local_datetime_to_utc(local_dt)
        response = app.get("/runs/%s/jobs/%s/" % (run_name, 1))
        assert response.json["updated"] == str(utc_dt)

    def test_filter_running_jobs(self, app, job_conf):
        app.post_json(
            "/runs/filter_running/jobs/", job_conf | {"status": "running"}
        )
        app.post_json(
            "/runs/filter_running/jobs/",
            job_conf | {"status": "running", "job_id": "2"},
        )
        app.put_json(
            "/runs/filter_running/jobs/1/", dict(success=True, status="pass")
        )
        response = app.get("/runs/filter_running/jobs/?status=running")
        assert len(response.json) == 1

    def test_timestamp_fields(self, app, job_conf):
        timestamp = datetime.now().replace(microsecond=0)
        app.post_json(
            "/runs/RUN/jobs/",
            job_conf
            | {
                "status": "queued",
                "timestamp": timestamp.strftime(TEUTHOLOGY_TIMESTAMP_FMT),
            },
        )
        response = app.get("/runs/RUN/jobs/")
        jobs = response.json
        for job in jobs:
            assert datetime.fromisoformat(job["posted"])
            assert datetime.fromisoformat(job["updated"])
            assert datetime.fromisoformat(job["timestamp"])
            assert datetime.fromisoformat(job["timestamp"]) == timestamp
