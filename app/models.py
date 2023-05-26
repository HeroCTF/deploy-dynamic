from app.database import db
from datetime import datetime


class Instances(db.Model):
    """
        id (int) : Primary key.
        user_id (int) : CTFd User ID.
        user_name (str) : CTFd User name.
        team_id (int) : CTFd Team ID.
        team_name (str) : CTFd Team name.
        docker_image (str) : Docker image deployed by the user.
        ports (str) : Port mapped for the docker instance.
        instance_name (str) : Random name for the instance.
        docker_client_id (int) : Challenges hosts ID.
        creation_date (date) : Date of instance creation.
    """

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, unique=False, nullable=False)
    user_name = db.Column(db.String(128), unique=False, nullable=False)
    team_id = db.Column(db.Integer, unique=False, nullable=False)
    team_name = db.Column(db.String(128), unique=False, nullable=False)

    challenge_name = db.Column(db.String(128), unique=False, nullable=False)
    network_name = db.Column(db.String(128), unique=False, nullable=False)
    ip_address = db.Column(db.String(32), unique=False, nullable=False)
    instance_name = db.Column(db.String(128), unique=True, nullable=False)
    docker_image = db.Column(db.String(128), unique=False, nullable=False)
    host_domain = db.Column(db.String(128), unique=False, nullable=False)
    ports = db.Column(db.String(256), unique=False, nullable=True)

    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"[{self.id}] {self.docker_image} on port {self.port}, created at {self.creation_date}."
