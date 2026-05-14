import asyncio
import json
import threading
from queue import Queue

import httpx
import pytest
import requests


@pytest.fixture
def single_test_node(machine_type, paddles_server):
    name = "single-lock-race-node"
    response = requests.post(
        f"{paddles_server}/nodes/",
        json.dumps(dict(name=name, machine_type=machine_type, up=True, locked=False)),
    )
    assert response.ok, f"{response.status_code} {response.text}"
    yield name
    response = requests.delete(f"{paddles_server}/nodes/{name}/")
    assert response.ok, f"{response.status_code} {response.text}"


def _lock_single_node(paddles_server, node_name, locked_by, description):
    return requests.post(
        f"{paddles_server}/nodes/{node_name}/lock/",
        json.dumps(
            dict(
                locked=True,
                locked_by=locked_by,
                description=description,
            )
        ),
        headers={"content-type": "application/json"},
    )


@pytest.fixture
def user_count():
    return 20


@pytest.fixture
def user_names(user_count):
    return [f"user{i + 1:03}" for i in range(user_count)]


@pytest.fixture
def node_count() -> int:
    return 20


@pytest.fixture
def node_names(node_count):
    return [f"node{i + 1:03}" for i in range(node_count)]


@pytest.fixture
def machine_type():
    return "mtype"


@pytest.fixture
def test_nodes(node_names, machine_type, paddles_server):
    for name in node_names:
        response = requests.post(
            f"{paddles_server}/nodes/",
            json.dumps(
                dict(name=name, machine_type=machine_type, up=True, locked=False)
            ),
        )
        assert response.ok, f"{response.status_code} {response.text}"
    assert len(requests.get(f"{paddles_server}/nodes/").json()) == len(node_names)
    yield
    for name in node_names:
        response = requests.delete(f"{paddles_server}/nodes/{name}/")
        assert response.ok, f"{response.status_code} {response.text}"
    assert requests.get(f"{paddles_server}/nodes/").json() == []


class TestNodesLockingRace(object):
    nodes_per_attempt = 2
    attempts_per_user = 2
    queue_size = 0

    @pytest.mark.asyncio
    async def test_node_lock_race_async(
        self,
        paddles_server,
        user_count,
        user_names,
        machine_type,
        node_count,
        test_nodes,
    ):
        attempts_remaining = {user: self.attempts_per_user for user in user_names}
        requests_ = []
        async with httpx.AsyncClient() as client:
            while sum(attempts_remaining.values()):
                for user in attempts_remaining.keys():
                    request = client.post(
                        f"{paddles_server}/nodes/lock_many/",
                        json=dict(
                            count=self.nodes_per_attempt,
                            machine_type=machine_type,
                            description=f"desc {user}",
                            locked_by=user,
                        ),
                    )
                    requests_.append(request)
                    attempts_remaining[user] -= 1
            responses = await asyncio.gather(*requests_)

        expected_successes = min(
            (node_count / self.nodes_per_attempt),
            (user_count * self.attempts_per_user),
        )
        assert (
            len([resp for resp in responses if resp.status_code == 200])
            == expected_successes
        )

        response = requests.get(f"{paddles_server}/nodes/")
        assert response.ok
        nodes = response.json()
        assert len(nodes) == node_count
        for node in nodes:
            assert node["locked"] is True, f"{node['name']} not locked as expected"

    def test_node_lock_race_threaded(
        self, paddles_server, user_names, machine_type, node_count, test_nodes
    ):
        def lock_attempt(user, count):
            response = requests.post(
                f"{paddles_server}/nodes/lock_many/",
                json.dumps(
                    dict(
                        count=count,
                        machine_type=machine_type,
                        description=f"desc {user}",
                        locked_by=user,
                    )
                ),
                headers={"content-type": "application/json"},
            )
            return dict(text=response.text, status=response.status_code)

        in_queue = Queue(maxsize=self.queue_size)
        out_queue = Queue()

        def worker():
            while not in_queue.empty():
                item = in_queue.get(timeout=1)
                result = lock_attempt(item["user"], item["count"])
                out_queue.put({"user": item["user"], "result": result["status"]})
                in_queue.task_done()

        attempts_remaining = {user: self.attempts_per_user for user in user_names}
        while sum(attempts_remaining.values()):
            for user in attempts_remaining.keys():
                in_queue.put({"user": user, "count": self.nodes_per_attempt})
                attempts_remaining[user] -= 1
        threading.Thread(target=worker, daemon=True).start()

        in_queue.join()
        response = requests.get(f"{paddles_server}/nodes/")
        assert response.ok
        nodes = response.json()
        assert len(nodes) == node_count
        for node in nodes:
            assert node["locked"] is True, f"{node['name']} not locked as expected"
        assert len(response.json()) == node_count
        assert set([node["locked"] for node in response.json()]) == {True}


class TestSingleNodeLockingRace(object):
    def test_single_node_lock_race_threaded(
        self, paddles_server, machine_type, single_test_node
    ):
        """
        Concurrent single-node locking should allow only one client to succeed.

        This test repeatedly races two lock requests against the same node and
        asserts the invariant that each round yields one success and one
        rejection. On buggy implementations, a round may allow two successes.
        """

        rounds = 100

        for round_num in range(rounds):
            current_node = requests.get(f"{paddles_server}/nodes/{single_test_node}/").json()
            if current_node["locked"]:
                unlock_response = requests.post(
                    f"{paddles_server}/nodes/{single_test_node}/lock/",
                    json.dumps(
                        dict(
                            locked=False,
                            locked_by=current_node["locked_by"],
                            description=current_node["description"],
                        )
                    ),
                    headers={"content-type": "application/json"},
                )
                assert unlock_response.ok, unlock_response.text

            results = Queue()
            start_barrier = threading.Barrier(3)

            def lock_attempt(user):
                start_barrier.wait()
                response = _lock_single_node(
                    paddles_server=paddles_server,
                    node_name=single_test_node,
                    locked_by=user,
                    description=f"lock by {user} round {round_num}",
                )
                results.put(
                    {
                        "user": user,
                        "status": response.status_code,
                        "body": response.text,
                    }
                )

            workers = [
                threading.Thread(target=lock_attempt, args=("user-a",)),
                threading.Thread(target=lock_attempt, args=("user-b",)),
            ]
            for worker in workers:
                worker.start()

            start_barrier.wait()

            for worker in workers:
                worker.join()

            responses = [results.get(), results.get()]
            statuses = [response["status"] for response in responses]
            assert statuses.count(200) == 1, (
                f"round {round_num} expected exactly one successful lock; "
                f"got responses={responses}"
            )


class TestNodesControllerNew(object):
    def test_lock_many_threaded(
        self, paddles_server, user_names, machine_type, node_count, test_nodes
    ):
        num_per_attempt = node_count

        def lock_attempt(user, queue):
            response = requests.post(
                f"{paddles_server}/nodes/lock_many/",
                json.dumps(
                    dict(
                        count=num_per_attempt,
                        machine_type=machine_type,
                        description="desc",
                        locked_by=user,
                    )
                ),
                headers={"content-type": "application/json"},
            )
            results = queue.get()
            results.append(dict(text=response.text, status_int=response.status_code))
            queue.put(results)

        jobs = []
        queue = Queue()
        queue.put([])
        for user in user_names:
            proc = threading.Thread(target=lock_attempt, args=(user, queue))
            jobs.append(proc)
        for job in jobs:
            job.start()
        for job in jobs:
            job.join()
        results = queue.get()
        statuses = [result["status_int"] for result in results]
        should_succeed = min(len(user_names), int(node_count / num_per_attempt))
        assert statuses.count(200) == should_succeed
        got_nodes = requests.get(
            f"{paddles_server}/nodes/?machine_type={machine_type}"
        ).json()
        statuses = [node["locked"] for node in got_nodes]
        print(statuses)
        num_locked = statuses.count(True)
        assert num_locked == should_succeed * num_per_attempt
