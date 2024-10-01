import typing

from docker import DockerClient


class UserType(typing.TypedDict):
    user_id: int | None
    username: str | None

    team_id: int | None
    team_name: str | None

    is_admin: bool


class ConfigDockerHostType(typing.TypedDict):
    domain: str
    api: str
    client: DockerClient


class ContainerPortType(typing.TypedDict):
    port: str
    protocol: typing.Literal["http", "ssh"]


class ChallengeContainerType(typing.TypedDict):
    docker_image: str

    hostname: str | None
    ports: list[ContainerPortType]

    command: str | None
    environment: dict[str, typing.Any] | None
    privileged: bool | None

    mem_limit: str
    read_only: bool

    cpu_period: int | None
    cpu_quota: int | None


class ConfigChallengeType(typing.TypedDict):
    name: str
    containers: list[ChallengeContainerType]
