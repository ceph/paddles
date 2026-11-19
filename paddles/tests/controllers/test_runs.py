import pytest

from sqlalchemy import select

from paddles.models import Job, Run


class TestRunController:
    def test_get_root(self, app):
        response = app.get("/runs/")
        assert response.status_int == 200

    def test_get_not_found(self, app):
        assert app.get("/runs/new_run/", expect_errors=True).status_int == 404

    def test_get_invalid_url_on_run(self, app):
        assert (
            app.get("/runs/new_run/invalid", expect_errors=True).status_int == 404
        )

    def test_post_valid_body(self, app):
        response = app.post_json("/runs/", dict(name="foo"))
        assert response.status_int == 200
        assert response.json == {}

    def test_create_new_run(self, app, session):
        app.post_json("/runs/", dict(name="foo"))
        assert session.scalars(select(Run).where(Run.name == "foo")).one().name == "foo"

    def test_allows_waiting_status(self, app, session, job_conf):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json("/runs/foo/jobs/", job_conf | {"status": "waiting"})
        new_run = session.scalars(select(Run).where(Run.name == "foo")).one()
        assert new_run.jobs
        assert new_run.status == "waiting"

    def test_running_status_with_waiting_and_running_jobs(self, app, session, job_conf):
        session = session
        app.post_json("/runs/", dict(name="foo"))
        app.post_json("/runs/foo/jobs/", job_conf | {"status": "running"})
        app.post_json(
            "/runs/foo/jobs/", job_conf | {"status": "waiting", "job_id": "2"}
        )
        new_run = session.scalars(select(Run).where(Run.name == "foo")).one()
        assert new_run.status == "running"
        assert session.scalars(select(Job)).first()

    def test_create_then_get_new_run(self, app, job_conf):
        app.post_json("/runs/", job_conf | {"name": "foo"})
        response = app.get("/runs/")
        result = response.json[0]
        assert result["name"] == "foo"

    def test_no_json_posted(self, app):
        # this is just posting a dict in the body, no proper headers
        response = app.post("/runs/", dict(), expect_errors=True)
        assert response.status_int == 400
        assert response.json["message"] == "could not decode JSON body"

    def test_create_new_job(self, app, session, job_conf):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json("/runs/foo/jobs/", job_conf | dict(status="queued"))
        new_job = session.scalars(select(Job).where(Job.job_id == "1")).one()
        assert new_job.job_id == "1"

    def test_delete_empty_run(self, app):
        app.post_json("/runs/", dict(name="foo"))
        app.delete("/runs/foo/")
        response = app.get("/runs/foo/", expect_errors=True)
        assert response.status_int == 404

    def test_delete_full_run(self, app):
        app.post_json("/runs/", dict(name="foo"))
        app.post_json("/runs/foo/", dict(user="test"))
        app.post_json("/runs/foo/", dict(job_id="9"))
        app.post_json("/runs/foo/", dict(job_id="12345"))
        app.delete("/runs/foo/")
        response = app.get("/runs/foo/jobs/12345/", expect_errors=True)
        assert response.status_int == 404

    def test_slice_valid(self, app):
        app.post_json("/runs/", dict(name="slice_valid"))
        print(app.get("/runs/slice_valid/").json)
        response = app.get("/runs/?fields=name,status")
        assert response.json == [
            dict(
                name="slice_valid",
                status="empty",
            )
        ]

    def test_runs_by_branch(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/branch/master/")
        assert response.json[0]["name"] == run_b_name

    def test_runs_by_suite(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/suite/rados/")
        assert response.json[0]["name"] == run_a_name

    def test_runs_by_branch_then_status(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/branch/master/status/empty/")
        assert response.json[0]["name"] == run_b_name

    def test_runs_by_branch_then_suite(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/branch/master/suite/big/")
        assert response.json[0]["name"] == run_b_name

    def test_runs_by_suite_then_branch(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/suite/rados/branch/next/")
        assert response.json[0]["name"] == run_a_name

    def test_get_branches(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/branch/")
        assert sorted(response.json) == ["master", "next"]

    def test_get_suites(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/suite/")
        assert sorted(response.json) == ["big", "rados"]

    def test_get_suites_since_runs_by_branch(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-plana"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/branch/master/suite/")
        assert response.json == ["big"]

    def test_get_machine_types(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-vps"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/machine_type/")
        assert response.json == ["plana", "vps"]

    def test_get_runs_by_machine_types(self, app):
        run_a_name = "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana"
        run_b_name = "teuthology-2013-01-02_00:00:00-big-master-testing-basic-vps"
        app.post_json("/runs/", dict(name=run_a_name))
        app.post_json("/runs/", dict(name=run_b_name))
        response = app.get("/runs/machine_type/vps/")
        assert response.json[0]["name"] == run_b_name

    def test_queued_fully(self, app, job_conf):
        run_names = ["run_one", "run_two"]
        for run_name in run_names:
            app.post_json("/runs/", dict(name=run_name))
            app.post_json(
                f"/runs/{run_name}/jobs/", job_conf | {"status": "queued"}
            )
            app.post_json(
                f"/runs/{run_name}/jobs/",
                job_conf | {"status": "queued", "job_id": "2"},
            )

        result = app.get("/runs/queued/").json
        result_names = sorted([r["name"] for r in result])
        assert result_names == sorted(run_names)

    def test_queued_partially(self, app, job_conf):
        run_names = ["run_one", "run_two"]
        for run_name in run_names:
            app.post_json("/runs/", dict(name=run_name))
            app.post_json(
                f"/runs/{run_name}/jobs/", job_conf | {"status": "queued"}
            )
            app.post_json(
                f"/runs/{run_name}/jobs/",
                job_conf | {"status": "dead", "job_id": "2"},
            )

        result = app.get("/runs/queued/").json
        result_names = sorted([r["name"] for r in result])
        assert result_names == sorted(run_names)


class TestRunControllerDateFilters:
    @pytest.fixture(scope="function", autouse=True)
    def runs(self, app):
        self.day1_runs = [
            "teuthology-2013-01-01_00:00:00-rados-next-testing-basic-plana",
            "teuthology-2013-01-01_00:00:01-nfs-next-testing-basic-plana",
            "teuthology-2013-01-01_00:00:02-rados-master-testing-basic-plana",
            "teuthology-2013-01-01_00:00:03-nfs-master-testing-basic-plana",
        ]
        self.day2_runs = [
            "teuthology-2013-01-02_00:00:00-rados-next-testing-basic-plana",
            "teuthology-2013-01-02_00:00:01-nfs-next-testing-basic-plana",
            "teuthology-2013-01-02_00:00:02-rados-master-testing-basic-plana",
            "teuthology-2013-01-02_00:00:03-nfs-master-testing-basic-plana",
        ]
        self.day3_runs = [
            "teuthology-2013-01-03_00:00:00-rados-next-testing-basic-plana",
            "teuthology-2013-01-03_00:00:01-nfs-next-testing-basic-plana",
            "teuthology-2013-01-03_00:00:02-rados-master-testing-basic-plana",
            "teuthology-2013-01-03_00:00:03-nfs-master-testing-basic-plana",
        ]
        self.day4_runs = [
            "teuthology-2013-01-04_00:00:00-rados-next-testing-basic-plana",
            "teuthology-2013-01-04_00:00:01-nfs-next-testing-basic-plana",
            "teuthology-2013-01-04_00:00:02-rados-master-testing-basic-plana",
            "teuthology-2013-01-04_00:00:03-nfs-master-testing-basic-plana",
        ]
        for run in self.day1_runs + self.day2_runs + self.day3_runs + self.day4_runs:
            app.post_json("/runs/", dict(name=run))

    def test_date_filter_finds_runs(self, app):
        response = app.get("/runs/date/2013-01-02/")
        assert response.status_int == 200
        got_names = [run["name"] for run in response.json]
        assert got_names == sorted(self.day2_runs, reverse=True)

    def test_bad_date_returns_error(self, app):
        response = app.get("/runs/date/2097-13-32/", expect_errors=True)
        assert response.json.get("message").startswith("date format must match")

    def test_date_range_filter_finds_runs(self, app):
        response = app.get("/runs/date/from/2013-01-02/to/2013-01-03/")
        got_names = [run["name"] for run in response.json]
        assert sorted(got_names) == sorted(self.day2_runs + self.day3_runs)

    def test_bad_date_range_returns_error(self, app):
        response = app.get(
            "/runs/date/from/yesterday/to/2097-13-32/", expect_errors=True
        )
        assert response.json.get("message").startswith("date format must match")

    def test_branch_and_since(self, app):
        response = app.get("/runs/branch/next/?since=2013-01-03")
        got_names = sorted(run["name"] for run in response.json)
        assert got_names == self.day3_runs[0:2] + self.day4_runs[0:2]

    def test_suite_and_since(self, app):
        response = app.get("/runs/suite/nfs/?since=2013-01-03")
        got_names = sorted(run["name"] for run in response.json)
        assert got_names == (self.day3_runs + self.day4_runs)[1::2]

    def test_suite_and_branch_and_since(self, app):
        response = app.get("/runs/suite/nfs/branch/next/?since=2013-01-03")
        got_names = sorted(run["name"] for run in response.json)
        assert got_names == [self.day3_runs[1], self.day4_runs[1]]


class TestRunControllerDateFiltersUTC:
    def test_branch_and_since(self, app, monkeypatch):
        import pytz

        import paddles.util

        monkeypatch.setattr(paddles.util, "localtz", pytz.UTC)

        day3_runs = [
            "teuthology-2013-01-03_00:00:00-rados-next-testing-basic-plana",
            "teuthology-2013-01-03_00:00:01-nfs-next-testing-basic-plana",
        ]
        day4_runs = [
            "teuthology-2013-01-04_00:00:00-rados-next-testing-basic-plana",
            "teuthology-2013-01-04_00:00:01-nfs-next-testing-basic-plana",
        ]
        for run in day3_runs + day4_runs:
            app.post_json("/runs/", dict(name=run))

        response = app.get("/runs/branch/next/?since=2013-01-03")
        got_names = sorted(run["name"] for run in response.json)
        assert got_names == day3_runs + day4_runs
