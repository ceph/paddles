class TestErrorEndpoints:
    def test_missing_run_jobs_list(self, app):
        response = app.get("/runs/nonexistent-run/jobs/", expect_errors=True)
        assert response.status_code == 404
        assert response.content_type == "application/json"
        assert "not found" in response.json["message"].lower()

    def test_invalid_json_body(self, app):
        response = app.post(
            "/runs/",
            params="not json",
            headers={"Content-Type": "application/json"},
            expect_errors=True,
        )
        assert response.status_code == 400
        assert response.content_type == "application/json"
        assert "json" in response.json["message"].lower()

    def test_invalid_node_count(self, app):
        response = app.get("/nodes/?count=not-a-number", expect_errors=True)
        assert response.status_code == 400
        assert response.content_type == "application/json"
        assert "integer" in response.json["message"].lower()

    def test_node_lock_requires_locked_by(self, app):
        app.post_json("/nodes/", {"name": "test-node"})
        response = app.put_json(
            "/nodes/test-node/lock/",
            {"locked": True},
            expect_errors=True,
        )
        assert response.status_code == 400
        assert response.content_type == "application/json"
        assert "locked_by" in response.json["message"].lower()

    def test_unknown_url_returns_json_404(self, app):
        response = app.get("/a/bogus/url", expect_errors=True)
        assert response.status_code == 404
        assert response.content_type == "application/json"
        assert "message" in response.json

    def test_missing_run_returns_json_404(self, app):
        response = app.get("/runs/does-not-exist/", expect_errors=True)
        assert response.status_code == 404
        assert response.content_type == "application/json"
        assert "not found" in response.json["message"].lower()

    def test_missing_job_returns_json_404(self, app):
        app.post_json("/runs/", {"name": "foo"})
        response = app.get("/runs/foo/jobs/999/", expect_errors=True)
        assert response.status_code == 404
        assert response.content_type == "application/json"
        assert "not found" in response.json["message"].lower()
