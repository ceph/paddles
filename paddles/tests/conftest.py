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
        response = requests.get(f"{paddles_url}/")
        response.raise_for_status()
        # Verify it's actually the Paddles server by checking for JSON response
        # (not HTML from another application)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            pytest.skip("Server at URL is not Paddles (wrong content-type); skipping")
        yield paddles_url
    except Exception:
        pytest.skip("Cannot find paddles server; skipping")
