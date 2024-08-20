import contextlib
import logging
from distutils.util import strtobool
from os import getenv
from secrets import token_hex

from flask import Flask

from app.database import db


def create_app() -> Flask:
    app = Flask(__name__)

    app.logger.setLevel(logging.DEBUG)
    app.secret_key = token_hex()

    app.debug = False
    with contextlib.suppress(ValueError):
        app.debug = strtobool(getenv("DEBUG", "0"))

    app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["ENABLE_RECAPTCHA"] = False
    with contextlib.suppress(ValueError):
        app.config["ENABLE_RECAPTCHA"] = strtobool(
            getenv("ENABLE_RECAPTCHA", "0")
        )
    app.config["RECAPTCHA_SITE_KEY"] = getenv("RECAPTCHA_SITE_KEY", "")
    app.config["RECAPTCHA_SECRET_KEY"] = getenv("RECAPTCHA_SECRET_KEY", "")

    db.init_app(app)
    with app.app_context():
        db.create_all()

    return app
