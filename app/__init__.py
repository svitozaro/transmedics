import os
import secrets
from pathlib import Path

from flask import Flask, abort, request, session

from .models import db


def _secret_key(instance: Path) -> str:
    """Use SECRET_KEY if set, otherwise create one random key per install."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = instance / "secret_key"
    if not path.exists():
        path.write_text(secrets.token_hex(32))
    return path.read_text().strip()


def _default_base_url():
    """Links in emails. Inside GitHub Codespaces, use the codespace's forwarded address."""
    name = os.environ.get("CODESPACE_NAME")
    domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    port = os.environ.get("PORT", "8000")
    if name and domain:
        return f"https://{name}-{port}.{domain}"
    return f"http://127.0.0.1:{port}"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    instance = Path(app.instance_path)
    instance.mkdir(parents=True, exist_ok=True)

    app.config.update(
        SECRET_KEY=_secret_key(instance),
        # Swap for PostgreSQL later, e.g. postgresql+psycopg://user:pass@host/db
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{instance / 'scheduler.db'}"),
        # "outbox" keeps emails inside the app. "smtp" sends them for real.
        EMAIL_BACKEND=os.environ.get("EMAIL_BACKEND", "outbox"),
        SMTP_HOST=os.environ.get("SMTP_HOST", ""),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_USER=os.environ.get("SMTP_USER", ""),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
        EMAIL_FROM=os.environ.get(
            "EMAIL_FROM", "TransMedics Aviation <aviation-scheduler@transmedics.com>"),
        # Used to build links in emails.
        BASE_URL=os.environ.get("BASE_URL") or _default_base_url(),
        # Only @transmedics.com addresses can be accounts (structure item 4).
        ALLOWED_EMAIL_DOMAIN=os.environ.get("ALLOWED_EMAIL_DOMAIN", "transmedics.com"),
        # Shows the "fill random preferences" button. Turn off when hosted.
        TEST_TOOLS=os.environ.get("TEST_TOOLS", "1") == "1",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            token = session.get("csrf")
            if not token or request.form.get("csrf") != token:
                abort(400, "Your form expired. Go back, reload the page and try again.")

    brand_dir = Path(app.static_folder) / "brand"

    def logo_file():
        for name in ("logo.svg", "logo.png", "logo.jpg", "logo.jpeg", "logo.webp"):
            if (brand_dir / name).exists():
                return "brand/" + name
        return None

    @app.context_processor
    def inject():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        from .auth import current_user
        return {"csrf_token": session["csrf"], "me": current_user(), "logo": logo_file(),
                "test_tools": app.config["TEST_TOOLS"],
                "email_backend": app.config["EMAIL_BACKEND"]}

    from . import admin, auth, pilot
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(pilot.bp)
    return app
