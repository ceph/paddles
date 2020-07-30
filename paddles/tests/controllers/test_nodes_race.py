try:
    from queue import Queue
except:
    from Queue import Queue

import threading
import requests
import json
import pytest

base_uri = 'http://localhost:8080'


class TestNodesControllerNew(object):
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

    def test_lock_many_threaded(self):
        # For debugging
        # print requests.get(base_uri + '/nodes/?machine_type=multi').json()

        def lock_attempt(user, queue):
            response = requests.post(
                base_uri + '/nodes/lock_many/',
                json.dumps(dict(count=self.num_per_attempt,
                                machine_type=self.mtype, description='desc',
                                locked_by=user)),
                headers={'content-type': 'application/json'},
            )
            results = queue.get()
            results.append(dict(text=response.text,
                                status_int=response.status_code))
            # For debugging
            # print user, response.status_code, response.text
            queue.put(results)

        jobs = []
        queue = Queue()
        queue.put([])
        for user in self.users:
            proc = threading.Thread(target=lock_attempt, args=(user, queue))
            jobs.append(proc)
        for job in jobs:
            job.start()
        for job in jobs:
            job.join()
        results = queue.get()
        statuses = [result['status_int'] for result in results]
        should_succeed = min(self.num_users, int(self.num_nodes /
                                                 self.num_per_attempt))
        assert statuses.count(200) == should_succeed
        got_nodes = requests.get(base_uri +
                                 '/nodes/?machine_type=multi').json()
        statuses = [node['locked'] for node in got_nodes]
        num_locked = statuses.count(True)
        assert num_locked == should_succeed * self.num_per_attempt
