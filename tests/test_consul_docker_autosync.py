# pylint: disable=redefined-outer-name
import time

import pytest
from consul import Consul

from consul_docker_autosync import __version__
from consul_docker_autosync.autosync import sync

consul = Consul()


@pytest.fixture
def sync_wrapper(docker, consul):
    return lambda: sync(docker, consul)


def test_syncs_containers_with_labels(sync_wrapper, start_container):
    container = start_container()
    sync_wrapper()
    services = consul.agent.services()
    assert len(services) == 1
    service = services["rafa-benitez"]
    assert service["Service"] == "rafa-benitez"
    assert service["Port"] == 8000
    assert service["Meta"] == {"container_id": container.id}


def test_ignores_containers_without_labels(sync_wrapper, start_container):
    start_container(labels={})
    sync_wrapper()
    assert consul.agent.services() == {}


def test_removes_dead_containers(sync_wrapper, start_container):
    container = start_container()
    sync_wrapper()
    container.stop()
    sync_wrapper()
    assert consul.agent.services() == {}


def test_http_check(sync_wrapper, start_container):
    start_container(
        labels={
            "CONSUL_SERVICE_NAME": "rafa-benitez",
            "CONSUL_SERVICE_PORT": "8000",
            "CONSUL_SERVICE_CHECK_HTTP": "http://localhost:8000/health",
            "CONSUL_SERVICE_CHECK_INTERVAL": "0.1s",
        }
    )
    sync_wrapper()
    time.sleep(1)
    checks = consul.agent.checks()
    assert len(checks) == 1
    check = list(checks.values())[0]
    assert check["Type"] == "http"
    assert check["Status"] == "passing"


def test_script_check(sync_wrapper, start_container):
    start_container(
        labels={
            "CONSUL_SERVICE_NAME": "rafa-benitez",
            "CONSUL_SERVICE_PORT": "8000",
            "CONSUL_SERVICE_CHECK_SCRIPT": "ls /",
            "CONSUL_SERVICE_CHECK_INTERVAL": "0.1s",
        }
    )
    sync_wrapper()
    time.sleep(1)
    checks = consul.agent.checks()
    assert len(checks) == 1
    check = list(checks.values())[0]
    assert check["Type"] == "script"
    assert check["Status"] == "passing"


@pytest.mark.parametrize(
    "labels",
    [{"CONSUL_SERVICE_NAME": "foo"}, {"CONSUL_SERVICE_PORT": "bar"}],
)
def test_ignores_containers_without_required_labels(
    labels, sync_wrapper, start_container
):
    start_container(labels=labels)
    sync_wrapper()
    assert consul.agent.services() == {}


def test_multiple(sync_wrapper, start_container):
    start_container(
        command="-listen=:8001 -text=ok",
        labels={"CONSUL_SERVICE_NAME": "one", "CONSUL_SERVICE_PORT": "8001"},
    )
    start_container(
        command="-listen=:8002 -text=ok",
        labels={"CONSUL_SERVICE_NAME": "two", "CONSUL_SERVICE_PORT": "8002"},
    )
    sync_wrapper()
    assert len(consul.agent.services()) == 2
