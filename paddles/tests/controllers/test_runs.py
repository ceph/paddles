from paddles.models import Run, Job
from paddles.tests import TestApp


class TestRunController(TestApp):

    def test_get_root(self):
        response = self.app.get('/runs/')
        assert response.status_int == 200

    def test_get_not_found(self):
        response = self.app.get('/runs/bogus/url', expect_errors=True)
        assert response.status_int == 404

    def test_post_invalid(self):
        response = self.app.post_json('/runs/', dict(), expect_errors=True)
        assert response.status_int == 400

    def test_get_invalid_url_on_run(self):
        response = self.app.get('/runs/suck/', expect_errors=True)
        assert response.status_int == 404
        assert response.json == {'message': 'requested run resource does not exist'}

    def test_post_valid_body(self):
        response = self.app.post_json('/runs/', dict(name="foo"))
        assert response.status_int == 200
        assert response.json == {}

    def test_create_new_run(self):
        self.app.post_json('/runs/', dict(name="foo"))
        new_run = Run.get(1)
        assert new_run.name == 'foo'

    def test_create_then_get_new_run(self):
        self.app.post_json('/runs/', dict(name="foo"))
        response = self.app.get('/runs/')
        result = response.json[0]
        assert result['name'] == 'foo'

    def test_no_json_posted(self):
        # this is just posting a dict in the body, no proper headers
        response = self.app.post('/runs/', dict(), expect_errors=True)
        assert response.status_int == 400
        assert response.json['message'] == 'could not decode JSON body'

    def test_create_new_job(self):
        self.app.post_json('/runs/', dict(name="foo"))
        self.app.post_json('/runs/foo/jobs/', dict(
            job_id=1,
        ))
        new_job = Job.get(1)
        assert new_job.job_id == '1'

    def test_delete_empty_run(self):
        self.app.post_json('/runs/', dict(name='foo'))
        self.app.delete('/runs/foo/')
        response = self.app.get('/runs/foo/', expect_errors=True)
        assert response.status_int == 404

    def test_delete_full_run(self):
        self.app.post_json('/runs/', dict(name='foo'))
        self.app.post_json('/runs/foo/', dict(job_id='42'))
        self.app.post_json('/runs/foo/', dict(job_id='9'))
        self.app.post_json('/runs/foo/', dict(job_id='12345'))
        self.app.delete('/runs/foo/')
        response = self.app.get('/runs/foo/jobs/12345/', expect_errors=True)
        assert response.status_int == 404

    def test_slice_valid(self):
        self.app.post_json('/runs/', dict(name='foo'))
        response = self.app.get('/runs/?fields=name,status')
        assert response.json == [dict(
            name='foo',
            status='finished',
        )]


