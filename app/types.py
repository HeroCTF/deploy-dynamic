import typing


class UserType(typing.TypedDict):
    user_id: int | None
    username: str | None

    team_id: int | None
    team_name: str | None

    is_admin: bool
