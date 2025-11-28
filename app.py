#!/usr/bin/env python3
from datetime import datetime, timedelta
from typing import Any

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_recaptcha import ReCaptcha

from app.app import create_app
from app.auth import admin_required, login_required
from app.config import (
    ADMIN_ONLY,
    CHALLENGES,
    CTFD_URL,
    MAX_INSTANCE_COUNT,
    MAX_INSTANCE_DURATION,
    MAX_INSTANCE_PER_TEAM,
    WEBSITE_TITLE,
)
from app.models import Instances
from app.utils import (
    check_access_key,
    check_challenge_name,
    create_instances,
    get_challenge_count_per_team,
    get_challenge_info,
    get_total_instance_count,
    remove_all_instances,
    remove_container_by_id,
    remove_old_instances,
    remove_user_running_instance,
)

app = create_app()
recaptcha = ReCaptcha(app)
recaptcha.theme = "dark"


def render(template: str, **kwargs: Any) -> str:
    """
    Shortcut for the render_template flask function.
    """
    return render_template(
        template,
        title=WEBSITE_TITLE,
        ctfd_url=CTFD_URL,
        max_instance_duration=MAX_INSTANCE_DURATION,
        max_instance_per_team=MAX_INSTANCE_PER_TEAM,
        challenges_option=CHALLENGES,
        instances_count=get_total_instance_count(),
        **kwargs,
    )


@app.route("/admin", methods=["GET"])
@admin_required
def admin():
    """
    Admin dashboard with all instances.
    """
    return render("admin.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle login process and form.
    """
    if session and session["verified"]:
        return redirect(url_for("index"))

    if request.method == "GET":
        return render("login.html")

    if request.method == "POST":
        access_key = (
            request.form["access_key"] if "access_key" in request.form else None
        )

        if not access_key:
            return render(
                "login.html", error=True, message="Please provide an access key."
            )

        success, message, user = check_access_key(access_key)
        if not success:
            return render("login.html", error=True, message=message)

        if ADMIN_ONLY and not user["is_admin"]:
            return render(
                "login.html",
                error=True,
                message="You need to be an administrator to login.",
            )

        session["verified"] = True
        session["user_id"] = user["user_id"]
        session["user_name"] = user["username"]
        session["team_id"] = user["team_id"]
        session["team_name"] = user["team_name"]
        session["admin"] = user["is_admin"]

        return redirect(url_for("index"))
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
@login_required
def index():
    """
    Display running instances of your team and allows you to submit new instances.
    """
    instances = Instances.query.filter_by(team_id=session["team_id"]).all()

    if instances:
        challenges_info = {}

        for instance in instances:
            if instance.network_name not in challenges_info:
                challenges_info[instance.network_name] = []

            remaining = timedelta(minutes=MAX_INSTANCE_DURATION) - (
                datetime.utcnow() - instance.creation_date
            )
            if remaining > timedelta(seconds=0):
                remaining = (
                    f"{remaining.seconds // 60:02d}m{remaining.seconds % 60:02d}s"
                )
            else:
                remaining = "This instance will be deleted shortly..."

            challenges_info[instance.network_name].append(
                {
                    "name": instance.challenge_name,
                    "host": instance.host_domain,
                    "hostname": instance.hostname,
                    "ip_address": instance.ip_address,
                    "ports": instance.ports,
                    "user_name": instance.user_name,
                    "time_remaining": remaining,
                }
            )

        return render(
            "index.html",
            challenges=CHALLENGES,
            captcha=recaptcha,
            challenges_info=challenges_info,
        )
    return render("index.html", challenges=CHALLENGES, captcha=recaptcha)


@app.route("/container/all", methods=["GET"])
@admin_required
def get_all_containers():
    """
    Admin restricted function to retrieve all containers.
    """
    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "id": instance.id,
                    "team": instance.team_name,
                    "username": instance.user_name,
                    "image": instance.docker_image,
                    "ports": instance.ports,
                    "instance_name": instance.instance_name,
                    "date": instance.creation_date,
                }
                for instance in Instances.query.all()
            ],
        }
    )


@app.route("/container/all", methods=["DELETE"])
@admin_required
def remove_containers():
    """
    Admin restricted function to remove all containers.
    """
    remove_all_instances()

    return jsonify({"success": True, "message": "Instances removed successfully."})


@app.route("/container/<int:container_id>", methods=["DELETE"])
@admin_required
def remove_container(container_id=None):
    """
    Admin restricted function to remove a container with its ID.
    """
    remove_container_by_id(container_id)

    return jsonify({"success": True, "message": "Instances removed successfully."})


@app.route("/remove/me", methods=["GET"])
@login_required
def remove_me():
    """
    Allow a user to remove their current instance.
    """
    if remove_user_running_instance(session["user_id"]):
        return jsonify({"success": True, "message": "Instance removed successfully."})

    return jsonify(
        {"success": False, "message": "Unable to find an instance to remove."}
    )


@app.route("/logout", methods=["GET"])
def logout():
    """
    Logout the user.
    """
    keys = list(session.keys())
    for key in keys:
        session.pop(key, None)

    return redirect(url_for("login"))


@app.route("/run_instance", methods=["POST"])
@login_required
def run_instance():
    """
    Allow a user to create a new instance.
    """
    challenge_name = request.form.get("challenge_name", None)

    if current_app.config["ENABLE_RECAPTCHA"] and not recaptcha.verify():
        flash("Captcha failed.", "red")
        return redirect(url_for("index"))

    if not challenge_name or challenge_name.strip() == "":
        flash("Please provide a challenge name.", "red")
        return redirect(url_for("index"))

    remove_old_instances()

    if not check_challenge_name(challenge_name):
        flash("The challenge name is not valid.", "red")
        return redirect(url_for("index"))

    if get_challenge_count_per_team(session["team_id"]) >= MAX_INSTANCE_PER_TEAM:
        flash(
            f"Your team has reached the maximum number of concurrent running instances ({MAX_INSTANCE_PER_TEAM}).",
            "red",
        )
        return redirect(url_for("index"))

    remove_user_running_instance(session["user_id"])

    if get_total_instance_count() > MAX_INSTANCE_COUNT:
        flash(
            f"The maximum number of dynamic instances has been reached (max: {MAX_INSTANCE_COUNT}).",
            "red",
        )
        return redirect(url_for("index"))

    challenge_info = get_challenge_info(challenge_name)

    nb_container = 0
    try:
        nb_container = create_instances(session, challenge_info)
    except Exception as e:
        current_app.logger.error(f"Error while creating instances: {e}")

    if nb_container == 1:
        flash(f"{nb_container} container is starting for {challenge_name}...", "green")
    elif nb_container > 1:
        flash(
            f"{nb_container} containers are starting for {challenge_name}...", "green"
        )
    else:
        flash(
            "An error occurred while creating your instance. Please contact an administrator.",
            "red",
        )

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
