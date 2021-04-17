import threading
from urllib.parse import urlparse

import click
import docker as dockerlib
from consul import Consul
from loguru import logger

from .autosync import sync
from .http_server import start_http_server

HTTP_TIMEOUT = 5  # seconds


@click.command()
@click.option(
    "--interval",
    default=10,
    type=float,
    show_default=True,
)
@click.option(
    "--docker-url",
    default="unix://var/run/docker.sock",
    show_default=True,
)
@click.option(
    "--consul-url",
    default="http://127.0.0.1:8500",
    show_default=True,
)
@click.option(
    "--consul-token",
    default=None,
    show_default=True,
)
@click.option(
    "--port",
    type=int,
    default=14400,
    show_default=True,
    help="The port to listen on",
)
def run(interval, docker_url, consul_url, consul_token, port):
    logger.info(
        "Starting consul-docker-autosync " + "consul={} docker={} sync_interval={}",
        consul_url,
        docker_url,
        interval,
    )
    docker = dockerlib.DockerClient(base_url=docker_url, timeout=HTTP_TIMEOUT)
    consul_address = urlparse(consul_url)
    consul = Consul(
        host=consul_address.hostname,
        port=consul_address.port,
        scheme=consul_address.scheme,
        token=consul_token,
        timeout=HTTP_TIMEOUT,
    )
    start_http_server(port)
    sync_wrapper = lambda: sync(docker, consul)
    sync_wrapper()
    set_interval(sync_wrapper, interval)


def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        try:
            func()
        except Exception:  # pylint: disable=broad-except
            logger.exception("Exception during execution, rescheduling sync")

    thread = threading.Timer(sec, func_wrapper)
    thread.start()
