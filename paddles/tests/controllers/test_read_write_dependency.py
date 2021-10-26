try:
    from queue import Queue
except:
    from Queue import Queue

import threading
import requests
import json
import pytest
import time
import random

base_uri = 'http://localhost:8080'


class TestReadWriteDependency(object):
    def setup_class(cls):
        try:
            assert requests.get(base_uri + '/nodes/').ok
        except Exception:
            pytest.skip("Cannot find paddles server; skipping")
    
    def setup_method(self, meth):
        self.num_nodes = 10
        self.mtype = 'multi'
        self.names = ['%s%s' % (self.mtype, i) for i in range(self.num_nodes)]
        self.num_users = 20
        self.users = ['user%s' % i for i in range(self.num_users)]
        self.num_per_attempt = self.num_nodes / 1
        self.create_or_update_nodes()

    def create_or_update_nodes(self):
        if requests.get('%s/nodes/%s/' % (base_uri, self.names[-1])).ok:
            self.unlock_nodes()
        else:
            for name in self.names:
                req = dict(name=name, machine_type=self.mtype, locked=False,
                           up=True)
                resp = requests.post(base_uri + '/nodes/', json.dumps(req),
                                     headers={'content-type':
                                              'application/json'})
                resp.raise_for_status()
    
    def unlock_nodes(self):
        for name in self.names:
            resp = requests.get('%s/nodes/%s/' % (base_uri, name))
            resp.raise_for_status()
            resp_d = resp.json()
            if not resp_d.get('locked', True):
                continue
            req = dict(locked=False, up=True,
                       locked_by=resp_d.get('locked_by'))
            resp = requests.put('%s/nodes/%s/lock/' % (base_uri, name),
                                json.dumps(req),
                                headers={'content-type': 'application/json'})
            resp.raise_for_status()
            resp = requests.get('%s/nodes/%s/' % (base_uri, name))
            resp.raise_for_status()
            assert not resp.json().get('locked')

    def teardown_method(self, meth):
        self.unlock_nodes()

    def lock_nodes(self):
        for user in self.users:
            requests.post(
                base_uri + '/nodes/lock_many/',
                json.dumps(dict(count=self.num_per_attempt,
                                machine_type=self.mtype, description='desc',
                                locked_by=user)),
                headers={'content-type': 'application/json'},
            )

    def test_unlock_many_threaded(self):

        def unlock_attempt(name, queue):
                resp = requests.get('%s/nodes/%s/' % (base_uri, name))
                resp.raise_for_status()
                resp_d = resp.json()
                
                req = dict(locked=False, up=True,
                        locked_by=resp_d.get('locked_by'))
                attempts = 1
                while attempts > 0:
                    response = requests.put('%s/nodes/%s/lock/' % (base_uri, name),
                                        json.dumps(req),
                                        headers={'content-type': 'application/json'})
                    if response.ok:
                        break
                    print(f'Raced updating node status, retries left: {attempts}')
                    attempts -= 1
                    if attempts:
                        time.sleep(random.uniform(0, 1))
                response.raise_for_status()
                queue.put(dict(text=response.text,
                               status_int=response.status_code))

        jobs = []
        queue = Queue()
        self.create_or_update_nodes()
        self.lock_nodes()
        for name in self.names:
            proc = threading.Thread(target=unlock_attempt, args=(name, queue))
            jobs.append(proc)
        for job in jobs:
            job.start()
        for job in jobs:
            job.join()
        results = []
        while not queue.empty():
            results.append(queue.get())
        statuses = [result['status_int'] for result in results]
        assert statuses.count(200) == len(statuses)
        got_nodes = requests.get(base_uri +
                                 '/nodes/?machine_type=multi').json()
        lock_status = [node['locked'] for node in got_nodes]
        num_unlocked = lock_status.count(False)
        assert num_unlocked == len(statuses)
