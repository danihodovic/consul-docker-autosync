# pylint: disable=invalid-name,redefined-outer-name
import os
import threading
import time

import pytest
import requests
from click.testing import CliRunner

from consul_docker_autosync.cli import run


@pytest.fixture
def run_threaded_cli(find_free_port):
    def fn(port=None):
        port = port or find_free_port()
        consul_host = os.getenv("CONSUL_HOST", "localhost")
        f = lambda: CliRunner().invoke(
            run,
            [
                f"--port={port}",
                "--interval=0.5",
                f"--consul-url=http://{consul_host}:8500",
                "--docker-url=unix://var/run/docker.sock",
            ],
        )
        threading.Thread(target=f, daemon=True).start()

    return fn


def test_cli(run_threaded_cli, start_container, consul):
    run_threaded_cli()
    start_container()
    time.sleep(1)
    assert len(consul.agent.services()) == 1


def test_health_check(run_threaded_cli, find_free_port):
    port = find_free_port()
    run_threaded_cli(port)
    time.sleep(1)
    res = requests.get(f"http://0.0.0.0:{port}/health")
    res.raise_for_status()
