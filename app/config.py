#!/usr/bin/env python3
from distutils.util import strtobool
from json import load
from os import getenv
from pathlib import Path

from docker import DockerClient

from app.types import ConfigChallengeType, ConfigDockerHostType


try:
    DEBUG = strtobool(getenv("DEBUG", "0"))
except ValueError:
    DEBUG = False


try:
    ADMIN_ONLY = strtobool(getenv("ADMIN_ONLY", "0"))
except ValueError:
    ADMIN_ONLY = False


with Path("config.json").open() as config_file:
    config = load(config_file)

    WEBSITE_TITLE = config["website_title"]
    CTFD_URL = config["ctfd_url"].rstrip("/")

    MAX_INSTANCE_COUNT = config["max_instance_count"]
    MAX_INSTANCE_DURATION = config["max_instance_duration"]
    MAX_INSTANCE_PER_TEAM = config["max_instance_per_team"]
    MIN_PORTS = config["random_ports"]["min"]
    MAX_PORTS = config["random_ports"]["max"]

    CHALLENGES: list[ConfigChallengeType] = config["challenges"]
    DOCKER_HOSTS: list[ConfigDockerHostType] = config["hosts"]

    for host in DOCKER_HOSTS:
        host["client"] = DockerClient(base_url=host["api"])
