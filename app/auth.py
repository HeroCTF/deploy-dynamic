from functools import wraps

from flask import redirect, session, url_for


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session and session["verified"]:
            return f(*args, **kwargs)
        else:
            return redirect(url_for("login"))

    return wrap


def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session and session["admin"]:
            return f(*args, **kwargs)
        else:
            return redirect(url_for("index"))

    return wrap
