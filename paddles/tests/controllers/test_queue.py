import time


class TestQueueController:
    def test_get_root(self, app):
        response = app.get("/")
        assert response.status_int == 200

    def test_create_queue(self, app):
        response = app.post_json("/queue/", dict(queue="test_queue"))
        assert response.status_code == 200

    def test_create_existing_queue(self, app):
        app.post_json("/queue/", dict(queue="test_queue"))
        response = app.post_json(
            "/queue/", dict(queue="test_queue"), expect_errors=True
        )
        assert response.status_code == 400

    def test_get_queue(self, app):
        app.post_json("/queue/", dict(queue="test_queue"))
        response = app.get("/queue/")
        assert len(response.json) == 1
        assert response.json[0]["queue"] == "test_queue"
        assert response.status_code == 200

    def test_fail_create_queue(self, app):
        response = app.post_json("/queue/", expect_errors=True)
        assert response.status_code == 400

    def test_priority_queue(self, app, job_conf_no_id):
        """
        Add 2 jobs with different priorities
        Check if popping the queue returns the higher priority job
        """
        app.post_json("/queue/", dict(queue="test_queue"))
        app.post_json("/runs/", dict(name="testrun"))
        response = app.post_json(
            "/runs/testrun/jobs/",
            job_conf_no_id
            | dict(
                queue="test_queue",
                priority=10,
                status="queued",
                name="job1",
            ),
        )
        assert response.json["job_id"] is not None
        app.post_json(
            "/runs/testrun/jobs/",
            job_conf_no_id
            | dict(
                queue="test_queue",
                priority=15,
                status="queued",
                name="job2",
            ),
        )

        top_job = app.get("/queue/pop_queue?queue=test_queue")
        assert response.json["job_id"] == top_job.json["job_id"]

    def test_queue_stats(self, app, job_conf_no_id):
        app.post_json("/queue/", dict(queue="test_queue2"))
        app.post_json("/runs/", dict(name="testrun2"))
        app.post_json(
            "/runs/testrun2/jobs/",
            job_conf_no_id
            | dict(
                queue="test_queue2",
                priority=10,
                status="queued",
                name="job1",
            ),
        )

        response = app.post_json("/queue/stats/", dict(queue="test_queue2"))
        assert response.json["queued_jobs"] == 1

    def test_pause_queue(self, app):
        app.post_json("/queue/", dict(queue="test_queue3"))
        pause_duration = 0.05
        response = app.put_json(
            "/queue/",
            dict(
                queue="test_queue3",
                paused_by="tester",
                pause_duration=pause_duration,
            ),
        )
        assert response.status_code == 200
        response = app.get("/queue/?machine_type=test_queue3")
        assert response.json[0]["paused"] is True
        time.sleep(pause_duration / 2)
        response = app.get("/queue/?machine_type=test_queue3")
        assert response.json[0]["paused"] is True
        time.sleep(pause_duration / 2)
        response = app.get("/queue/?machine_type=test_queue3")
        assert response.json[0]["paused"] is False

    def test_get_queued_jobs(self, app, job_conf_no_id):
        app.post_json("/queue/", dict(queue="test_queue4"))
        app.post_json("/runs/", dict(name="testrun4"))
        app.post_json(
            "/runs/testrun4/jobs/",
            job_conf_no_id
            | dict(
                queue="test_queue4",
                priority=10,
                status="queued",
                name="job1",
                user="tester",
            ),
        )
        app.post_json(
            "/runs/testrun4/jobs/",
            job_conf_no_id
            | dict(
                queue="test_queue4",
                priority=15,
                status="queued",
                name="job2",
                user="tester",
            ),
        )
        app.post_json(
            "/runs/testrun4/jobs/",
            job_conf_no_id
            | dict(
                queue="test_queue4",
                priority=15,
                name="job3",
                user="tester",
            ),
        )

        response = app.get(
            "/queue/queued_jobs/?user=tester&queue=test_queue4",
        )

        assert response.status_code == 200
        assert len(response.json) == 3
        assert response.json[0]["user"] == "tester"
        assert response.json[1]["user"] == "tester"
