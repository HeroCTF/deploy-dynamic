from flask import session, redirect, url_for

from functools import wraps


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
