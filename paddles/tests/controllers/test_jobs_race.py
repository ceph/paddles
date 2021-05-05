try:
    from queue import Queue
except:
    from Queue import Queue

from datetime import datetime
import threading
import requests
import json
import pytest
import time
import random

base_uri = 'http://localhost:8080'


class TestJobsControllerRace(object):
    def setup_class(cls):
        try:
            assert requests.get(base_uri + '/runs/').ok
        except Exception:
            pytest.skip("Cannot find paddles server; skipping")

    def setup_method(self, meth):
        self.run = 'test-jobs-' + datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
        resp = requests.post(base_uri + '/runs/',
                             data=json.dumps(dict(name=self.run)),
                             headers={'content-type': 'application/json'})
        resp.raise_for_status()

    def teardown_method(self, meth):
        resp = requests.delete(base_uri + '/runs/' + self.run + '/')
        resp.raise_for_status()

    def test_job_create_threaded(self):

        def job_update(job_id, status):
            job_data = dict(job_id=job_id, status=status, run=self.run, name=str(job_id))
            headers = {'content-type': 'application/json'}
            run_uri = base_uri + '/runs/' + self.run + '/jobs/'

            attempts = 5
            while attempts > 0:
                response = requests.post(
                    run_uri,
                    data=json.dumps(job_data),
                    headers=headers,
                )
                print(job_data, response.status_code, response.text)
                try:
                    resp_json = response.json()
                except ValueError:
                    resp_json = dict()

                if resp_json:
                    msg = resp_json.get('message', '')
                else:
                    msg = response.text

                if msg and msg.endswith('already exists'):
                    response = requests.put(
                        run_uri + str(job_id) + '/',
                        data=json.dumps(job_data),
                        headers=headers,
                    )
                if response.ok:
                    break
                print(f'Raced updating job {job_id} status, retries left: {attempts}')
                attempts -= 1
                time.sleep(random.uniform(0, 1))
            response.raise_for_status()

            queue.put(dict(text=response.text,
                           status_int=response.status_code))

        jobs = []
        queue = Queue()
        job_ids = list(range(1, 10))
        for job_id in job_ids:
            for status in ['queued', 'queued', 'running', 'running']:
                jobs.append(threading.Thread(target=job_update, args=(job_id, status)))
        for job in jobs:
            job.start()
        for job in jobs:
            job.join()
        results = []
        while not queue.empty():
            results.append(queue.get())
        statuses = [result['status_int'] for result in results]
        assert statuses.count(200) == len(statuses)

        # check for duplicate rows by looking at status in at the run
        # and job level - this can be different when there are
        # duplicate rows created due to a race
        resp = requests.get(base_uri + '/runs/' + self.run + '/jobs/')
        assert resp.status_code == 200
        for job in resp.json():
            job_id = job['job_id']
            job_status_in_run = job['status']
            job_resp = requests.get(base_uri + '/runs/' + self.run + '/jobs/' + str(job_id) + '/')
            assert job_resp.status_code == 200
            assert job_resp.json()['status'] == job_status_in_run
        assert len(resp.json()) == len(job_ids)
