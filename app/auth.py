import hashlib
import secrets
from datetime import timedelta
from functools import wraps

from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from . import emailer
from .models import AuditLog, PasswordToken, User, db, now

bp = Blueprint("auth", __name__)

MIN_PASSWORD = 10


def current_user():
    if "user" not in g:
        uid = session.get("uid")
        u = db.session.get(User, uid) if uid else None
        g.user = u if (u and u.active) else None
    return g.user


def audit(action):
    u = current_user()
    db.session.add(AuditLog(actor=u.email if u else "system", action=action))


def password_problem(pw, confirm):
    if pw != confirm:
        return "The two passwords do not match."
    if len(pw) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if pw.isalpha() or pw.isdigit():
        return "Use a mix of letters and numbers or symbols."
    return None


def set_password(user, pw, must_change=False):
    user.password_hash = generate_password_hash(pw)
    user.must_change_password = must_change


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        u = current_user()
        if not u:
            return redirect(url_for("auth.login", next=request.path))
        if u.must_change_password and request.endpoint != "auth.change_password":
            return redirect(url_for("auth.change_password"))
        return view(*a, **kw)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*a, **kw):
        if not current_user().is_admin:
            return redirect(url_for("auth.home"))
        return view(*a, **kw)
    return wrapped


def pilot_required(view):
    @wraps(view)
    @login_required
    def wrapped(*a, **kw):
        if not current_user().is_pilot:
            return redirect(url_for("auth.home"))
        return view(*a, **kw)
    return wrapped


def make_token(user, purpose, days):
    raw = secrets.token_urlsafe(32)
    db.session.add(PasswordToken(
        user_id=user.id, purpose=purpose, expires_at=now() + timedelta(days=days),
        token_hash=hashlib.sha256(raw.encode()).hexdigest()))
    return f"{current_app.config['BASE_URL']}{url_for('auth.set_password_link', token=raw)}"


def send_invite(user):
    link = make_token(user, "invite", days=14)
    emailer.send(user.email, "Your vacation portal account",
                 f"Hello {user.first_name},\n\nAn account has been created for you on the "
                 f"TransMedics Aviation pilot vacation portal.\n\nChoose your password here "
                 f"(link valid for 14 days):\n{link}\n\nYour username is {user.email}.")


@bp.route("/")
def home():
    if User.query.count() == 0:
        return redirect(url_for("auth.setup"))
    u = current_user()
    if not u:
        return redirect(url_for("auth.login"))
    return redirect(url_for("admin.scheduler" if u.is_admin else "pilot.ranking"))


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    """First run only: create the first admin account."""
    if User.query.count() > 0:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        f = request.form
        email = f.get("email", "").strip().lower()
        problem = password_problem(f.get("password", ""), f.get("confirm", ""))
        domain = current_app.config["ALLOWED_EMAIL_DOMAIN"]
        if not email.endswith("@" + domain) or len(email) <= len(domain) + 1:
            problem = f"Use your @{domain} email address."
        if problem:
            flash(problem, "error")
        else:
            u = User(email=email, first_name=f.get("first_name", "").strip(),
                     last_name=f.get("last_name", "").strip(), role="ADMIN")
            set_password(u, f["password"])
            db.session.add(u)
            db.session.commit()
            session.clear()
            session["uid"] = u.id
            flash("Admin account created. Next, upload your pilot list.", "ok")
            return redirect(url_for("admin.users"))
    return render_template("auth/setup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if User.query.count() == 0:
        return redirect(url_for("auth.setup"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = User.query.filter_by(email=email, active=True).first()
        if u and u.password_hash and check_password_hash(u.password_hash,
                                                         request.form.get("password", "")):
            session.clear()
            session["uid"] = u.id
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//")
                            else url_for("auth.home"))
        flash("Wrong email or password.", "error")
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    u = current_user()
    if request.method == "POST":
        f = request.form
        problem = password_problem(f.get("password", ""), f.get("confirm", ""))
        if not check_password_hash(u.password_hash or "", f.get("current", "")):
            problem = "Your current password is not right."
        elif f.get("password") == f.get("current"):
            problem = "Choose a password different from the current one."
        if problem:
            flash(problem, "error")
        else:
            set_password(u, f["password"])
            db.session.commit()
            flash("Password changed.", "ok")
            return redirect(url_for("auth.home"))
    return render_template("auth/change_password.html", forced=u.must_change_password)


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = User.query.filter_by(email=email, active=True).first()
        if u:
            link = make_token(u, "reset", days=1)
            emailer.send(u.email, "Reset your vacation portal password",
                         f"Someone asked to reset the password for {u.email}.\n\n"
                         f"Use this link within 24 hours:\n{link}\n\n"
                         "If it was not you, you can ignore this email.")
            db.session.commit()
        # Same answer either way so the page does not reveal who has an account.
        flash("If that address has an account, a reset link has been emailed.", "ok")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot.html")


@bp.route("/set-password/<token>", methods=["GET", "POST"])
def set_password_link(token):
    t = PasswordToken.query.filter_by(
        token_hash=hashlib.sha256(token.encode()).hexdigest(), used=False).first()
    if not t or t.expires_at < now() or not t.user.active:
        flash("That link has expired or was already used. Ask for a new one.", "error")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        problem = password_problem(request.form.get("password", ""),
                                   request.form.get("confirm", ""))
        if problem:
            flash(problem, "error")
        else:
            set_password(t.user, request.form["password"])
            t.used = True
            db.session.commit()
            session.clear()
            session["uid"] = t.user.id
            flash("Password set. You are signed in.", "ok")
            return redirect(url_for("auth.home"))
    return render_template("auth/set_password.html", user=t.user)
