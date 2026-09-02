"""
Regression tests for the request flows teuthology and pulpito actually use,
written after running the SQLAlchemy 2 port against a copy of the Sepia
production database.
"""
import time
from datetime import datetime


def _parse(ts):
    return datetime.fromisoformat(ts)


class TestJobUpdates:
    def test_updated_advances_on_status_put(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        before = app.get("/runs/foo/jobs/1/").json
        run_before = app.get("/runs/foo/").json
        time.sleep(0.01)
        app.put_json("/runs/foo/jobs/1/", {"status": "running"})
        after = app.get("/runs/foo/jobs/1/").json
        run_after = app.get("/runs/foo/").json
        assert _parse(after["updated"]) > _parse(before["updated"])
        assert _parse(run_after["updated"]) > _parse(run_before["updated"])

    def test_updated_advances_on_empty_put(self, app, job_conf):
        # teuthology's supervisor watchdog PUTs without a status purely to
        # bump the job's updated time
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        before = app.get("/runs/foo/jobs/1/").json
        time.sleep(0.01)
        app.put_json("/runs/foo/jobs/1/", {})
        after = app.get("/runs/foo/jobs/1/").json
        assert _parse(after["updated"]) > _parse(before["updated"])

    def test_client_supplied_updated_is_honored(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        app.put_json(
            "/runs/foo/jobs/1/", {"status": "pass", "updated": "2020-01-02 03:04:05.678"}
        )
        job = app.get("/runs/foo/jobs/1/").json
        assert job["updated"].startswith("2020-01-02")

    def test_success_is_stored_alongside_status(self, app, job_conf):
        # teuthology's set_status() always sends both
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        app.put_json("/runs/foo/jobs/1/", {"status": "pass", "success": True})
        job = app.get("/runs/foo/jobs/1/").json
        assert job["status"] == "pass"
        assert job["success"] is True

    def test_invalid_status_is_a_400(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        response = app.put_json(
            "/runs/foo/jobs/1/", {"status": "bogus"}, expect_errors=True
        )
        assert response.status_int == 400
        assert "status" in response.json["message"]

    def test_bad_timestamp_is_a_400(self, app, job_conf):
        response = app.post_json(
            "/runs/foo/jobs/",
            job_conf | {"name": "foo", "timestamp": "2026-09-01 16:55:47"},
            expect_errors=True,
        )
        assert response.status_int == 400

    def test_unknown_and_protected_keys_are_ignored(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        before = app.get("/runs/foo/jobs/1/").json
        response = app.put_json(
            "/runs/foo/jobs/1/",
            {"href": "x", "id": 12345, "posted": "1999-01-01 00:00:00", "no_such_column": 1},
        )
        assert response.status_int == 200
        after = app.get("/runs/foo/jobs/1/").json
        assert after["id"] == before["id"]
        assert after["posted"] == before["posted"]

    def test_null_queue_key_with_job_id_is_accepted(self, app, job_conf):
        # a job JSON round-tripped from paddles' own GET carries "queue": null
        response = app.post_json(
            "/runs/foo/jobs/", job_conf | {"name": "foo", "queue": None}
        )
        assert response.status_int == 200

    def test_duplicate_post_message(self, app, job_conf):
        # teuthology falls back to PUT only if the message ends this way
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        response = app.post_json(
            "/runs/foo/jobs/", job_conf | {"name": "foo"}, expect_errors=True
        )
        assert response.status_int == 400
        assert response.json["message"].endswith("already exists")

    def test_targets_on_put_link_nodes(self, app, job_conf):
        # teuthology creates the job first and sends targets later, once
        # nodes are locked
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        app.put_json(
            "/runs/foo/jobs/1/",
            {
                "status": "running",
                "targets": {"ubuntu@smithi001.front.sepia.ceph.com": "ssh-key"},
            },
        )
        response = app.get("/nodes/smithi001.front.sepia.ceph.com/jobs/")
        assert [job["job_id"] for job in response.json] == ["1"]
        node = app.get("/nodes/smithi001.front.sepia.ceph.com/").json
        assert node["machine_type"] == job_conf["machine_type"]


class TestRunStatus:
    def test_status_filter_uses_stored_column(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo", "status": "queued"})
        assert [r["name"] for r in app.get("/runs/status/queued/").json] == ["foo"]
        assert app.get("/runs/status/running/").json == []

        app.put_json("/runs/foo/jobs/1/", {"status": "running"})
        assert [r["name"] for r in app.get("/runs/status/running/").json] == ["foo"]
        assert app.get("/runs/status/queued/").json == []
        assert "running" in app.get("/runs/status/").json

        app.put_json("/runs/foo/jobs/1/", {"status": "pass"})
        assert [r["name"] for r in app.get("/runs/status/finished%20pass/").json] == ["foo"]

    def test_status_recomputed_on_job_delete(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo", "status": "running"})
        app.post_json(
            "/runs/foo/jobs/", job_conf | {"name": "foo", "job_id": "2", "status": "pass"}
        )
        assert app.get("/runs/foo/").json["status"] == "running"
        app.delete("/runs/foo/jobs/1/")
        assert app.get("/runs/foo/").json["status"] == "finished pass"
        assert [r["name"] for r in app.get("/runs/status/finished%20pass/").json] == ["foo"]

    def test_started_is_set_once(self, app, job_conf):
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo"})
        app.post_json("/runs/foo/jobs/", job_conf | {"name": "foo", "job_id": "2"})
        app.put_json("/runs/foo/jobs/1/", {"status": "running"})
        first = app.get("/runs/foo/").json["started"]
        assert first == app.get("/runs/foo/jobs/1/").json["started"]
        time.sleep(0.01)
        app.put_json("/runs/foo/jobs/2/", {"status": "running"})
        assert app.get("/runs/foo/").json["started"] == first
        app.put_json("/runs/foo/jobs/1/", {"status": "pass"})
        app.put_json("/runs/foo/jobs/2/", {"status": "pass"})
        assert app.get("/runs/foo/").json["started"] == first
