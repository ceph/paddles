from paddles.tests import TestApp
import time


class TestQueueController(TestApp):

    def test_get_root(self):
        response = self.app.get('/')
        assert response.status_int == 200

    def test_create_queue(self):
        response = self.app.post_json('/queue/', dict(queue="test_queue"))
        assert response.status_code == 200

    def test_create_existing_queue(self):
        self.app.post_json('/queue/', dict(queue="test_queue"))
        response = self.app.post_json('/queue/', dict(queue="test_queue"),
                                      expect_errors=True)
        assert response.status_code == 400

    def test_get_queue(self):
        self.app.post_json('/queue/', dict(queue="test_queue"))
        response = self.app.get('/queue/')
        assert len(response.json) == 1
        assert response.json[0]['queue'] == 'test_queue'
        assert response.status_code == 200

    def test_fail_create_queue(self):
        response = self.app.post_json('/queue/', expect_errors=True)
        assert response.status_code == 400

    def test_priority_queue(self):
        """
        Add 2 jobs with different priorities
        Check if popping the queue returns the higher priority job
        """
        self.app.post_json('/queue/', dict(queue="test_queue"))
        self.app.post_json('/runs/', dict(name="testrun"))
        response_1 = self.app.post_json('/runs/testrun/jobs/', dict(
            queue='test_queue',
            priority=10,
            status='queued',
            name='job1',
        ))
        self.app.post_json('/runs/testrun/jobs/', dict(
            queue='test_queue',
            priority=15,
            status='queued',
            name='job2',
        ))

        top_job = self.app.get('/queue/pop_queue?queue=test_queue')
        assert response_1.json['job_id'] == top_job.json['job_id']

    def test_queue_stats(self):
        self.app.post_json('/queue/', dict(queue="test_queue2"))
        self.app.post_json('/runs/', dict(name="testrun2"))
        self.app.post_json('/runs/testrun2/jobs/', dict(
            queue='test_queue2',
            priority=10,
            status='queued',
            name='job1',
        ))

        response = self.app.post_json('/queue/stats/', dict(queue="test_queue2"))
        assert response.json['queued_jobs'] == 1

    def test_pause_queue(self):
        self.app.post_json('/queue/', dict(queue="test_queue3"))
        pause_duration = 0.05
        response = self.app.put_json('/queue/', dict(
            queue="test_queue3",
            paused_by="tester",
            pause_duration=pause_duration,
        ))
        assert response.status_code == 200
        response = self.app.get('/queue/?machine_type=test_queue3')
        assert response.json[0]['paused'] is True
        time.sleep(pause_duration / 2)
        response = self.app.get('/queue/?machine_type=test_queue3')
        assert response.json[0]['paused'] is True
        time.sleep(pause_duration / 2)
        response = self.app.get('/queue/?machine_type=test_queue3')
        assert response.json[0]['paused'] is False

    def test_get_queued_jobs(self):
        self.app.post_json('/queue/', dict(queue="test_queue4"))
        self.app.post_json('/runs/', dict(name="testrun4"))
        self.app.post_json('/runs/testrun4/jobs/', dict(
            queue='test_queue4',
            priority=10,
            status='queued',
            name='job1',
            user='tester',
        ))
        self.app.post_json('/runs/testrun4/jobs/', dict(
            queue='test_queue4',
            priority=15,
            status='queued',
            name='job2',
            user='tester',
        ))
        self.app.post_json('/runs/testrun4/jobs/', dict(
            queue='test_queue4',
            priority=15,
            name='job3',
            user='tester',
        ))

        response = self.app.post_json('/queue/queued_jobs/?user=tester', dict(
            queue='test_queue4'
        ))

        assert response.status_code == 200
        assert len(response.json) == 2
        assert response.json[0]['user'] == 'tester'
        assert response.json[1]['user'] == 'tester'
