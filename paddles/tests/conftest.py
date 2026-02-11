from typing import Iterator

import pytest
import requests


@pytest.fixture
def job_conf_no_id():
    """
    A minimal job config object, without job_id
    """
    return {
        "name": "name",
        "machine_type": "mtype",
        "os_type": "OS",
        "os_version": "version",
    }


@pytest.fixture
def job_conf(job_conf_no_id):
    """
    A minimal job config object, with job_id
    """
    return job_conf_no_id | {"job_id": "1"}


@pytest.fixture
def paddles_url() -> str:
    return "http://localhost:8080"


@pytest.fixture
def paddles_server(paddles_url) -> Iterator[str]:
    try:
        requests.get(f"{paddles_url}/").raise_for_status()
        yield paddles_url
    except Exception:
        pytest.skip("Cannot find paddles server; skipping")
