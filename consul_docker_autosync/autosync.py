# pylint: disable=too-many-locals
from loguru import logger


def sync(docker, consul):
    logger.debug("Syncing docker containers as consul services")
    docker_containers = set()
    for container in docker.containers.list():
        if (
            "CONSUL_SERVICE_NAME" in container.labels
            and "CONSUL_SERVICE_PORT" in container.labels
        ):
            docker_containers.add(container.id)

    consul_containers = set()
    for _, service in consul.agent.services().items():
        if "container_id" in service["Meta"]:
            consul_containers.add(service["Meta"]["container_id"])

    containers_to_register = docker_containers - consul_containers
    for container_id in containers_to_register:
        container = docker.containers.get(container_id=container_id)
        labels = container.labels
        name = labels["CONSUL_SERVICE_NAME"]
        port = labels["CONSUL_SERVICE_PORT"]
        register_payload = dict(
            name=name,
            port=int(port),
            meta={"container_id": container.id},
        )
        if (
            "CONSUL_SERVICE_CHECK_HTTP" in labels
            or "CONSUL_SERVICE_CHECK_SCRIPT" in labels
        ):
            register_payload["check"] = check_from_labels(container)

        consul.agent.service.register(**register_payload)
        logger.info("Registered: {} @ port={}", container.name, port)

    containers_to_deregister = consul_containers - docker_containers
    for container_id in containers_to_deregister:
        container = docker.containers.get(container_id=container_id)
        consul.agent.service.deregister(container.labels["CONSUL_SERVICE_NAME"])
        logger.info("Deregistered: {}", container.name)


def check_from_labels(container):
    labels = container.labels
    prefix = "CONSUL_SERVICE_CHECK"
    check = {
        "Interval": labels.get(f"{prefix}_INTERVAL", "15s"),
        "Timeout": labels.get(f"{prefix}_CHECK_TIMEOUT", "5s"),
        # pylint: disable=line-too-long
        "DeregisterCriticalServiceAfter": labels.get(
            f"{prefix}_DEREGISTER_CRITICAL_SERVICE_AFTER", "1h"
        ),
    }
    if f"{prefix}_HTTP" in labels:
        return {
            **check,
            "HTTP": labels[f"{prefix}_HTTP"],
            "SuccessBeforePassing": int(
                labels.get(f"{prefix}_SUCCESS_BEFORE_PASSING", "3")
            ),
            "FailuresBeforeCritical": int(
                labels.get(f"{prefix}_FAILURES_BEFORE_CRITICAL", "3")
            ),
        }
    if f"{prefix}_SCRIPT" in labels:
        return {**check, "Args": labels[f"{prefix}_SCRIPT"].split(" ")}
    return {}
