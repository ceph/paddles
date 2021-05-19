from datetime import datetime
from paddles.tests import TestApp
from paddles.util import local_datetime_to_utc

class TestQueueController(TestApp):

    def test_get_root(self):
        response = self.app.get('/')
        assert response.status_int == 200


    def test_create_queue(self):
        response = self.app.post_json('/queue/', dict(machine_type="test_queue"))
        assert response.status_code == 200


    def test_create_existing_queue(self):
        self.app.post_json('/queue/', dict(machine_type="test_queue"))
        response = self.app.post_json('/queue/', dict(machine_type="test_queue"), 
                                    expect_errors=True)
        assert response.status_code == 400


    def test_get_queue(self):
        self.app.post_json('/queue/', dict(machine_type="test_queue"))
        response = self.app.get('/queue/')
        assert len(response.json) == 1
        assert response.json[0]['machine_type'] == 'test_queue'
        assert response.status_code == 200


    def test_fail_create_queue(self):
        response = self.app.post_json('/queue/', expect_errors=True)
        assert response.status_code == 400
    

    def test_priority_queue(self):
        """
        Add 2 jobs with different priorities
        Check if popping the queue returns the higher priority job
        """
        self.app.post_json('/queue/', dict(machine_type="test_queue"))
        self.app.post_json('/runs/', dict(name="testrun"))
        response_1 = self.app.post_json('/runs/testrun/jobs/', dict(
            machine_type='test_queue',
            priority=10,
            status='queued',
            name='job1',
        ))
        response_2 = self.app.post_json('/runs/testrun/jobs/', dict(
            machine_type='test_queue',
            priority=15,
            status='queued',
            name='job2',
        ))

        top_job = self.app.get('/queue/pop_queue?machine_type=test_queue')
        assert response_1.json['job_id'] == top_job.json['job_id']
    

    def test_queue_stats(self):
        self.app.post_json('/queue/', dict(machine_type="test_queue"))
        self.app.post_json('/runs/', dict(name="testrun"))
        self.app.post_json('/runs/testrun/jobs/', dict(
            machine_type='test_queue',
            priority=10,
            status='queued',
            name='job1',
        ))

        response = self.app.post_json('/queue/stats/', dict(machine_type="test_queue"))
        assert response.json['count'] == 1
    

    def test_pause_queue(self):
        self.app.post_json('/queue/', dict(machine_type="test_queue"))
        response = self.app.put_json('/queue/', dict(
            machine_type="test_queue",
            paused=True,
            paused_by="tester",
            pause_duration=30,
        ))
        assert response.status_code == 200
        response = self.app.get('/queue/?machine_type=test_queue')
        assert response.json[0]['paused'] == True
        """
        Try unpausing queue with different paused_by parameter
        """
        response = self.app.put_json('/queue/', dict(
            machine_type="test_queue",
            paused=False,
            paused_by="tester2",
        ), expect_errors=True)
        assert response.status_code == 403
        response = self.app.put_json('/queue/', dict(
            machine_type="test_queue",
            paused=False,
            paused_by="tester",
        ))
        assert response.status_code == 200

    
    def test_get_queued_jobs(self):
        self.app.post_json('/queue/', dict(machine_type="test_queue"))
        self.app.post_json('/runs/', dict(name="testrun"))
        self.app.post_json('/runs/testrun/jobs/', dict(
            machine_type='test_queue',
            priority=10,
            status='queued',
            name='job1',
            user='tester',
        ))
        self.app.post_json('/runs/testrun/jobs/', dict(
            machine_type='test_queue',
            priority=15,
            status='queued',
            name='job2',
            user='tester',
        ))
        self.app.post_json('/runs/testrun/jobs/', dict(
            machine_type='test_queue',
            priority=15,
            name='job3',
            user='tester',
        ))

        response = self.app.post_json('/queue/queued_jobs/', dict(
            machine_type='test_queue',
            user='tester'
        ))
        
        assert response.status_code == 200
        assert len(response.json) == 2
        assert response.json[0]['user'] == 'tester'
        assert response.json[1]['user'] == 'tester'
