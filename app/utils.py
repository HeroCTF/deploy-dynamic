#!/usr/bin/env python3
import datetime
import random
import re
import secrets
import typing

import flask
import requests
from docker.errors import APIError, ImageNotFound, NotFound
from docker.models.containers import Container
from flask import current_app

from app.config import (
    CHALLENGES,
    CTFD_URL,
    DOCKER_HOSTS,
    MAX_INSTANCE_DURATION,
    MAX_PORTS,
    MIN_PORTS,
)
from app.database import db
from app.models import Instances
from app.types import ConfigChallengeType, ConfigDockerHostType, UserType


if typing.TYPE_CHECKING:
    import docker


REQUESTS_TIMEOUT = 60


def remove_old_instances() -> None:
    """Remove old instances (creation_date > X minutes)."""
    instances = (
        db.session.query(Instances)
        .filter(
            Instances.creation_date
            < (
                datetime.datetime.now(datetime.UTC)
                - datetime.timedelta(minutes=MAX_INSTANCE_DURATION)
            )
        )
        .all()
    )

    # TODO: Remove all instances of a challenge.
    for instance in instances:
        remove_container_by_id(instance.id)


def remove_user_running_instance(user_id: int) -> int:
    """Remove instance if the user has already run an instance."""
    instances = Instances.query.filter_by(user_id=user_id).all()

    for instance in instances:
        current_app.logger.debug(
            "User n°%d is removing '%s'...", user_id, instance.instance_name
        )
        remove_container_by_id(instance.id)

    return len(instances) > 0


def find_ip_address(container: Container) -> str:
    """Find IP Address of a running container."""
    ret = container.exec_run("hostname -i")
    if ret.exit_code == 0:
        return ret.output.decode().strip()

    ret = container.exec_run("cat /etc/hosts")
    if ret.exit_code == 0:
        return ret.output.split()[-2].decode()

    return "UNKNOWN"


def create_instances(
        session: flask.session,
        challenge_info: ConfigChallengeType
) -> int:
    """Create new instances."""
    # Generate deploy environment
    deploy_config = {
        "network_name": secrets.token_hex(16),
        "host": random.choice(DOCKER_HOSTS),
        "containers": [],
    }
    worker: docker.DockerClient = deploy_config["host"]["client"]
    worker.networks.create(deploy_config["network_name"], driver="bridge")
    current_app.logger.debug(
        "Starting deployment '%s' for challenge '%s'.",
        deploy_config["network_name"],
        challenge_info["name"],
    )

    # Generate containers environment
    for container in challenge_info["containers"]:
        instance_name = secrets.token_hex(16)
        deploy_config["containers"].append(
            {
                "docker_image": container["docker_image"],
                "command": container.get("command", None),
                "hostname": container.get("hostname", instance_name),
                "instance_name": instance_name,
                "ports": {
                    pinfo["port"]: find_unused_port(deploy_config["host"])
                    for pinfo in container["ports"]
                },
                "protocols": [
                    pinfo["protocol"] for pinfo in container["ports"]
                ],
                "environment": container.get("environment", {}),
                "mem_limit": container.get("mem_limit", "512m"),
                "privileged": container.get("privileged", False),
                "read_only": container.get("read_only", False),
                "cpu_period": container.get("cpu_period", None),
                "cpu_quota": container.get("cpu_quota", None),
            }
        )

    current_app.logger.debug(
        "Environment for deployment '%s': %s",
        deploy_config["network_name"],
        deploy_config,
    )

    # Save instances in DB and run containers
    for container in deploy_config["containers"]:
        instance = Instances(
            user_id=session["user_id"],
            user_name=session["user_name"],
            team_id=session["team_id"],
            team_name=session["team_name"],
            docker_image=container["docker_image"],
            challenge_name=challenge_info["name"],
            network_name=deploy_config["network_name"],
            hostname=container["hostname"],
            ports=", ".join(
                f"{port}/{proto}"
                for port, proto in zip(
                    container["ports"].values(),
                    container["protocols"],
                    strict=False,
                )
            ),
            host_domain=deploy_config["host"]["domain"],
            instance_name=container["instance_name"],
        )

        try:
            created_container = worker.containers.run(
                image=container["docker_image"],
                command=container["command"],
                hostname=container["hostname"],
                name=container["instance_name"],
                ports=container["ports"],
                environment=container["environment"],
                network=deploy_config["network_name"],
                auto_remove=True,
                detach=True,
                mem_limit=container["mem_limit"],
                privileged=container["privileged"],
                read_only=container["read_only"],
                cpu_period=container["cpu_period"],
                cpu_quota=container["cpu_quota"],
            )
            instance.ip_address = find_ip_address(created_container)
        except ImageNotFound as err:
            current_app.logger.exception(
                "ImageNotFound: Unable to find %s, %s",
                container["docker_image"],
                err,
            )
            return -1

        db.session.add(instance)
        db.session.commit()

    return len(challenge_info["containers"])


def get_challenge_count_per_team(team_id: int) -> int:
    """Returns the number of challenges running for a specific team."""
    return (
        Instances.query.filter_by(team_id=team_id)
        .distinct(Instances.network_name)
        .count()
    )


def find_unused_port(docker_host: ConfigDockerHostType) -> int:
    """
    Find a port that is not used by any instances
    (on a specific challenge host).
    """
    containers = docker_host["client"].containers.list(all=True)
    found = False

    rand_port = random.randint(MIN_PORTS, MAX_PORTS + 1)

    while not found:
        found = True

        for container in containers:
            if rand_port in container.ports.values():
                found = False

        rand_port = random.randint(MIN_PORTS, MAX_PORTS + 1)

    return rand_port


def get_total_instance_count() -> int:
    """Returns the number of challenges instance running."""
    return Instances.query.count()


def get_challenge_info(challenge_name: str) -> ConfigChallengeType | None:
    """Returns challenge information with a challenge_name as parameter."""
    for challenge in CHALLENGES:
        if challenge["name"] == challenge_name:
            return challenge
    return None


def check_challenge_name(challenge_name: str) -> bool:
    """Returns True if the challenge_name is valid, else False."""
    return any(challenge["name"] == challenge_name for challenge in CHALLENGES)


def check_access_key(key: str) -> tuple[bool, str, UserType]:
    """Returns the user_id, user_name, team_id, team_name and is_admin."""
    user: UserType = {
        "user_id": None,
        "username": None,
        "team_id": None,
        "team_name": None,
        "is_admin": False,
    }

    pattern = r"^ctfd_[a-zA-Z0-9]+$"
    if not re.match(pattern, key):
        return False, "Invalid access key, wrong format!", user

    base_url = CTFD_URL.strip("/")
    try:
        resp_json = requests.get(
            f"{base_url}/api/v1/users/me",
            headers={
                "Authorization": f"Token {key}",
                "Content-Type": "application/json",
            },
            timeout=REQUESTS_TIMEOUT,
        ).json()

        success = resp_json.get("success", False)
        user["user_id"] = resp_json.get("data", {}).get("id", "")
        user["username"] = resp_json.get("data", {}).get("name", "")
        user["team_id"] = resp_json.get("data", {}).get("team_id", False)

        # User is not in a team
        if not success or not user["team_id"]:
            return False, "User not in a team or invalid token.", user

        resp_json = requests.get(
            f"{base_url}/api/v1/teams/{user['team_id']}",
            headers={
                "Authorization": f"Token {key}",
                "Content-Type": "application/json",
            },
            timeout=REQUESTS_TIMEOUT,
        ).json()
        user["team_name"] = resp_json.get("data", {}).get("name", "")

        resp_json = requests.get(
            f"{base_url}/api/v1/configs",
            headers={
                "Authorization": f"Token {key}",
                "Content-Type": "application/json",
            },
            timeout=REQUESTS_TIMEOUT,
        ).json()
        user["is_admin"] = resp_json.get("success", False)
        return True, "", user  # noqa: TRY300
    except Exception as err:
        current_app.logger.exception(
            "Unable to reach CTFd with access key: %s", key
        )
        current_app.logger.exception("Error: %s", str(err))

    return False, "An error has occurred.", user


def remove_all_instances() -> None:
    """Remove all running containers."""
    for instance in Instances.query.all():
        remove_container_by_id(instance.id)


def remove_container_by_name(host_domain: str, name: str) -> None:
    """Remove running container using its random name."""
    for docker_host in DOCKER_HOSTS:
        if host_domain in docker_host["domain"]:
            client = docker_host["client"]
            containers = client.containers.list(filters={"name": name})

            if len(containers):
                current_app.logger.debug("Removing container '%s'...", name)
                try:
                    containers[0].remove(force=True)

                    network_name = next(
                        containers[0]
                        .attrs["NetworkSettings"]["Networks"]
                        .keys()
                    )
                    networks = client.networks.list(
                        filters={"name": network_name}
                    )
                    networks[0].remove()
                except NotFound as err:
                    current_app.logger.warning(
                        "Unable to find the container to remove (name: '%s'): "
                        "%s",
                        name,
                        err,
                    )
                except KeyError as err:
                    current_app.logger.warning(
                        "Unable to find the network to remove (name: '%s'): "
                        "%s",
                        network_name,
                        err,
                    )
                except APIError as err:
                    current_app.logger.warning(
                        "Unable to remove the network (name: '%s'): %s",
                        network_name,
                        err,
                    )
                return


def remove_container_by_id(instance_id: int) -> None:
    """Remove running container using its instance ID."""
    instance = Instances.query.filter_by(id=instance_id).first()
    if instance:
        remove_container_by_name(instance.host_domain, instance.instance_name)
        db.session.delete(instance)
        db.session.commit()
