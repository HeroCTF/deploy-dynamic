#!/usr/bin/env python3
from os import getenv
from json import load

from docker import DockerClient


if getenv("DEBUG") and getenv("DEBUG").strip().upper() in ['1', 'TRUE']:
    DEBUG = True
else:
    DEBUG = False

if getenv("ADMIN_ONLY") and getenv("ADMIN_ONLY").strip().upper() in ['1', 'TRUE']:
    ADMIN_ONLY = True
else:
    ADMIN_ONLY = False

with open("config.json", "r") as config_file:
    config = load(config_file)

    WEBSITE_TITLE = config["website_title"]
    CTFD_URL = config["ctfd_url"].rstrip("/")

    MAX_INSTANCE_COUNT = config["max_instance_count"]
    MAX_INSTANCE_DURATION = config["max_instance_duration"]
    MAX_INSTANCE_PER_TEAM = config["max_instance_per_team"]
    MIN_PORTS = config["random_ports"]["min"]
    MAX_PORTS = config["random_ports"]["max"]


    CHALLENGES = config["challenges"]
    DOCKER_HOSTS = config["hosts"]

    for host in DOCKER_HOSTS:
        host["client"] = DockerClient(base_url=host["api"])
