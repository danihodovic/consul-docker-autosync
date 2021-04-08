# pylint: disable=redefined-outer-name
import docker as dockerlib
import pytest
from consul import Consul

TEST_CONTAINER_TAG = "consul-docker-autosync"


@pytest.fixture()
def consul():
    return Consul()


@pytest.fixture()
def docker():
    return dockerlib.from_env()


@pytest.fixture(autouse=True)
def clear_state(docker, consul):
    yield
    for container in docker.containers.list():
        project = container.labels.get("PROJECT", None)
        if project == TEST_CONTAINER_TAG:
            container.remove(force=True)

    for service in consul.agent.services():
        consul.agent.service.deregister(service)


@pytest.fixture()
def start_container(docker):
    def wrapper(**kwargs):
        defaults = dict(
            image="hashicorp/http-echo",
            command="-listen=:8000 -text=ok",
            detach=True,
            network_mode="host",
            labels={
                "CONSUL_SERVICE_NAME": "rafa-benitez",
                "CONSUL_SERVICE_PORT": "8000",
                "CONSUL_SERVICE_CHECK_HTTP": "http://localhost:8000/health",
                "CONSUL_SERVICE_CHECK_INTERVAL": "30s",
                "CONSUL_SERVICE_CHECK_SUCCESS_BEFORE_PASSING": "0",
                "CONSUL_SERVICE_CHECK_FAILURE_BEFORE_CRITICAL": "0",
            },
        )
        params = {**defaults, **kwargs}
        params["labels"]["PROJECT"] = TEST_CONTAINER_TAG  # type: ignore
        return docker.containers.run(**params)

    return wrapper


@pytest.fixture(scope="session")
def find_free_port():
    """
    https://gist.github.com/bertjwregeer/0be94ced48383a42e70c3d9fff1f4ad0
    """

    def _find_free_port():
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 0))
        portnum = s.getsockname()[1]
        s.close()

        return portnum

    return _find_free_port
