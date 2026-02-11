import concurrent.futures
import json
import random
import threading
import time
from datetime import datetime
from queue import Queue

import pytest
import requests

base_uri = "http://localhost:8080"


class TestJobsControllerRace(object):
    def setup_class(cls):
        try:
            assert requests.get(base_uri + "/runs/").ok
        except Exception:
            pytest.skip("Cannot find paddles server; skipping")

    def setup_method(self, meth):
        self.run = "test-jobs-" + datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        resp = requests.post(
            base_uri + "/runs/",
            data=json.dumps(dict(name=self.run)),
            headers={"content-type": "application/json"},
        )
        resp.raise_for_status()

    def teardown_method(self, meth):
        resp = requests.delete(base_uri + "/runs/" + self.run + "/")
        resp.raise_for_status()

    def test_job_create_threaded(self):
        def job_update(job_id, status):
            job_data_minimal = dict(
                job_id=job_id,
                status=status,
                run=self.run,
                name=str(job_id),
            )
            job_data_full = job_data_minimal | dict(
                machine_type="mtype",
                os_type="os",
                os_version="ver",
            )
            headers = {"content-type": "application/json"}
            run_uri = base_uri + "/runs/" + self.run + "/jobs/"

            created = False
            attempts = 1
            while attempts > 0:
                msg = None
                if not created:
                    response = requests.post(
                        run_uri,
                        data=json.dumps(job_data_full),
                        headers=headers,
                    )
                    if response.ok:
                        created = True
                    try:
                        resp_json = response.json()
                    except ValueError:
                        resp_json = dict()

                    if resp_json:
                        msg = resp_json.get("message", "")
                    else:
                        msg = response.text

                if msg and msg.endswith("already exists"):
                    created = True
                    response = requests.put(
                        run_uri + str(job_id) + "/",
                        data=json.dumps(job_data_minimal),
                        headers=headers,
                    )
                if response.ok:
                    break
                attempts -= 1
                print(f"Raced updating job {job_id} status, retries left: {attempts}")
                if attempts:
                    time.sleep(random.uniform(0, 1))
            response.raise_for_status()

            queue.put(dict(text=response.text, status_int=response.status_code))

        jobs = []
        queue = Queue()
        job_ids = list(range(1, 50))
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for job_id in job_ids:
                for status in ["queued", "queued", "running", "running"]:
                    futures.append(executor.submit(job_update, job_id, status))
            for future in concurrent.futures.as_completed(futures):
                future.result()
        results = []
        while not queue.empty():
            results.append(queue.get())
        statuses = [result["status_int"] for result in results]
        assert statuses.count(200) == len(statuses)

        jobs = []
        queue = Queue()
        for job_id in job_ids:
            jobs.append(threading.Thread(target=job_update, args=(job_id, "running")))
        for job in jobs:
            job.start()
        for job in jobs:
            job.join()
        results = []
        while not queue.empty():
            results.append(queue.get())
        statuses = [result["status_int"] for result in results]
        assert statuses.count(200) == len(statuses)

        # check for duplicate rows by looking at status in at the run
        # and job level - this can be different when there are
        # duplicate rows created due to a race
        resp = requests.get(base_uri + "/runs/" + self.run + "/jobs/")
        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) == len(job_ids)
        for job in resp.json():
            job_id = job["job_id"]
            job_status_in_run = job["status"]
            assert job_status_in_run == "running", f"{job_id=} status incorrect"
            job_resp = requests.get(
                base_uri + "/runs/" + self.run + "/jobs/" + str(job_id) + "/"
            )
            assert job_resp.status_code == 200
            print(f"{job_id=} {job_resp.json()['status']}")
            assert job_resp.json()["status"] == job_status_in_run
        got_ids = [j["job_id"] for j in resp.json()]
        assert len(resp.json()) == len(job_ids)
        assert sorted(list(map(int, got_ids))) == sorted(job_ids)
