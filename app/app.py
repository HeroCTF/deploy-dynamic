from flask import Flask
from app.database import db

import logging
from secrets import token_hex
from os import getenv


def create_app():
    app = Flask(__name__)

    app.secret_key = token_hex()
    app.debug = getenv("DEBUG", False) in ["1", "True", "TRUE"]
    app.logger.setLevel(logging.DEBUG)

    app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["ENABLE_RECAPTCHA"] = getenv("ENABLE_RECAPTCHA", False)
    app.config["RECAPTCHA_SITE_KEY"] = getenv("RECAPTCHA_SITE_KEY", "")
    app.config["RECAPTCHA_SECRET_KEY"] = getenv("RECAPTCHA_SECRET_KEY", "") 

    db.init_app(app)
    with app.app_context():
        db.create_all()

    return app
