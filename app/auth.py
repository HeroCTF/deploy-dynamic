import typing
from functools import wraps

import flask
from flask import redirect, session, url_for


P = typing.ParamSpec("P")
R = typing.TypeVar("R", bound=flask.Response)


def login_required(f: typing.Callable[P, R]) -> typing.Callable[P, R]:
    @wraps(f)
    def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
        if session and session["verified"]:
            return f(*args, **kwargs)
        return redirect(url_for("login"))

    return wrap


def admin_required(f: typing.Callable[P, R]) -> typing.Callable[P, R]:
    @wraps(f)
    def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
        if session and session["admin"]:
            return f(*args, **kwargs)
        return redirect(url_for("index"))

    return wrap
