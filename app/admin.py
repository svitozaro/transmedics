import csv
import io
import random
import secrets
from datetime import date
from pathlib import Path

from flask import (Blueprint, Response, current_app, flash, redirect,
                   render_template, request, url_for)

from . import csv_import, emailer, service
from . import settings as cfg
from .auth import (admin_required, audit, current_user, make_token, send_invite,
                   set_password)
from .models import (Assignment, AuditLog, EmailMessage, PasswordToken, Preference,
                     PublishedAssignment, User, db)

bp = Blueprint("admin", __name__, url_prefix="/admin")

ROLES = ["PIC", "SIC", "ADMIN"]


def _domain():
    return current_app.config["ALLOWED_EMAIL_DOMAIN"]


def _email_ok(email):
    if "@" not in email:
        return False
    # The first admin can use any address; everyone else must be on the company domain.
    return email.endswith("@" + _domain())


# ---------- user management ----------

@bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip().lower()
    people = User.query.order_by(User.role, User.hire_date, User.last_name).all()
    if q:
        people = [u for u in people if q in (u.full_name + " " + u.email).lower()]
    return render_template("admin/users.html", users=people, q=q, roles=ROLES,
                           domain=_domain())


def _apply_form(u, f):
    u.first_name = f.get("first_name", "").strip()
    u.last_name = f.get("last_name", "").strip()
    u.email = f.get("email", "").strip().lower()
    u.role = f.get("role") if f.get("role") in ROLES else "PIC"
    if u.is_pilot:
        u.group = f.get("group") if f.get("group") in ("A", "B") else None
        u.hire_date = csv_import.parse_date(f.get("hire_date", ""))
        if not u.group:
            raise ValueError("Pilots need a group (A or B).")
    else:
        u.group, u.hire_date = None, None
    if not _email_ok(u.email):
        raise ValueError(f"Email must be an @{_domain()} address.")


@bp.route("/users/new", methods=["POST"])
@admin_required
def user_new():
    u = User()
    try:
        _apply_form(u, request.form)
        if User.query.filter_by(email=u.email).first():
            raise ValueError(f"{u.email} already has an account.")
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("admin.users"))
    db.session.add(u)
    db.session.flush()
    send_invite(u)
    audit(f"created user {u.email} ({u.role})")
    db.session.commit()
    flash(f"Created {u.full_name}. An invitation email with a set-password link "
          "was sent (see Outbox).", "ok")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:uid>", methods=["GET", "POST"])
@admin_required
def user_edit(uid):
    u = db.get_or_404(User, uid)
    if request.method == "POST":
        try:
            old_email = u.email
            _apply_form(u, request.form)
            other = User.query.filter(User.email == u.email, User.id != u.id).first()
            if other:
                raise ValueError(f"{u.email} already belongs to another account.")
            if u.id == current_user().id and not u.is_admin:
                raise ValueError("You cannot remove your own admin role.")
            u.active = request.form.get("active") == "on" or u.id == current_user().id
            audit(f"edited user {old_email}")
            db.session.commit()
            flash("Saved.", "ok")
            return redirect(url_for("admin.users"))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
    return render_template("admin/user_edit.html", u=u, roles=ROLES)


@bp.route("/users/<int:uid>/temp-password", methods=["POST"])
@admin_required
def user_temp_password(uid):
    """Structure item 7: admins set/reset a pilot's password.
    A random temporary password is shown once; the user must change it at sign-in."""
    u = db.get_or_404(User, uid)
    temp = "-".join(secrets.token_urlsafe(4) for _ in range(3))
    set_password(u, temp, must_change=True)
    audit(f"set temporary password for {u.email}")
    db.session.commit()
    flash(f"Temporary password for {u.email}: {temp}  (shown only once; they must "
          "change it when they sign in)", "ok")
    return redirect(url_for("admin.user_edit", uid=uid))


@bp.route("/users/<int:uid>/send-link", methods=["POST"])
@admin_required
def user_send_link(uid):
    u = db.get_or_404(User, uid)
    send_invite(u)
    audit(f"sent set-password link to {u.email}")
    db.session.commit()
    flash(f"Set-password link emailed to {u.email}.", "ok")
    return redirect(url_for("admin.user_edit", uid=uid))


@bp.route("/users/<int:uid>/delete", methods=["POST"])
@admin_required
def user_delete(uid):
    u = db.get_or_404(User, uid)
    if u.id == current_user().id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))
    for model in (Assignment, PublishedAssignment, PasswordToken):
        model.query.filter_by(user_id=u.id).delete()
    audit(f"deleted user {u.email}")
    db.session.delete(u)
    db.session.commit()
    flash(f"Deleted {u.email}.", "ok")
    return redirect(url_for("admin.users"))


@bp.route("/users/invite-all", methods=["POST"])
@admin_required
def invite_all():
    todo = User.query.filter(User.password_hash.is_(None), User.active.is_(True)).all()
    for u in todo:
        send_invite(u)
    audit(f"sent invitations to {len(todo)} users")
    db.session.commit()
    flash(f"Sent {len(todo)} invitation(s) to users who have not set a password yet.", "ok")
    return redirect(url_for("admin.users"))


SAMPLE_CSV = Path(__file__).resolve().parent.parent / "sample_data" / "pilots_sample.csv"


@bp.route("/users/import", methods=["POST"])
@admin_required
def import_csv():
    if request.form.get("sample") and current_app.config["TEST_TOOLS"]:
        raw = SAMPLE_CSV.read_bytes()  # the 140 made-up pilots, for testing
    else:
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Choose a CSV file first.", "error")
            return redirect(url_for("admin.users"))
        raw = file.read()
    rows, errors = csv_import.parse(raw, _domain())
    if errors:
        flash("Nothing was imported. Fix these and upload again: " + " | ".join(errors[:15])
              + (" ..." if len(errors) > 15 else ""), "error")
        return redirect(url_for("admin.users"))
    created = updated = 0
    for r in rows:
        u = User.query.filter_by(email=r["email"]).first()
        if u and u.is_admin:
            flash(f"Skipped {u.email}: it is an admin account.", "error")
            continue
        if not u:
            u = User(email=r["email"])
            db.session.add(u)
            created += 1
        else:
            updated += 1
        for k in ("first_name", "last_name", "role", "group", "hire_date"):
            setattr(u, k, r[k])
        u.active = True
    audit(f"imported CSV: {created} new, {updated} updated")
    db.session.commit()
    flash(f"Imported {len(rows)} pilots: {created} new, {updated} updated. New pilots "
          "cannot sign in until you send invitations.", "ok")
    return redirect(url_for("admin.users"))


# ---------- scheduler ----------

@bp.route("/")
@bp.route("/scheduler")
@admin_required
def scheduler():
    cal = service.calendar()
    people = service.pilots()
    group = request.args.get("group", "")
    role = request.args.get("role", "")
    shown = [u for u in people if (not group or u.group == group)
             and (not role or u.role == role)]
    periods = [p for p in cal.periods if not group or p.group == group]
    assignments = Assignment.query.all()
    by_user = {a.user_id: a for a in assignments}
    prefs = {}
    for p in Preference.query.all():
        prefs.setdefault(p.user_id, {})[p.period] = p.rank
    counts = service.period_counts(assignments, people)
    crews = {p.key: service.crews_left(p.group, p.key, counts, people) for p in periods}
    published = {p.user_id: p.period for p in PublishedAssignment.query.all()}
    submitted = sum(1 for u in people if u.prefs_submitted_at)
    return render_template(
        "admin/scheduler.html", cal=cal, periods=periods, pilots=shown,
        total=len(people), by_user=by_user, prefs=prefs, counts=counts, crews=crews,
        caps=service.caps(), need=cfg.get_int("required_crews"),
        status=service.status(), problems=service.problems(cal, assignments, people),
        published=published, submitted=submitted, group=group, role=role,
        last_run=cfg.get("last_run_at"), last_published=cfg.get("last_published_at"),
        seniority={u.id: i + 1 for i, u in enumerate(people)},
        rankings_open=service.rankings_open())


@bp.route("/scheduler/run", methods=["POST"])
@admin_required
def run():
    if service.status() == "published":
        flash("Unpublish the schedule before running the scheduler again.", "error")
        return redirect(url_for("admin.scheduler"))
    results = service.run_scheduler()
    audit("ran the scheduler")
    db.session.commit()
    n = {"preference": 0, "rule11": 0, "none": 0}
    for r in results.values():
        n[r.source] += 1
    flash(f"Scheduler finished: {n['preference']} got a ranked week, {n['rule11']} were "
          f"assigned by Rule 11, {n['none']} could not be placed. Rankings are now locked. "
          "Review, adjust if needed, then publish.", "ok")
    return redirect(url_for("admin.scheduler"))


@bp.route("/scheduler/assign", methods=["POST"])
@admin_required
def assign():
    """Structure item 15: manual adjustment of the draft."""
    if service.status() != "draft":
        flash("Changes can only be made to a draft. Unpublish first.", "error")
        return redirect(url_for("admin.scheduler"))
    u = db.get_or_404(User, int(request.form["user_id"]))
    cal = service.calendar()
    period = request.form.get("period") or None
    if period and period not in cal.by_group.get(u.group, []):
        flash("That is not one of this pilot's duty weeks.", "error")
        return redirect(url_for("admin.scheduler"))
    a = Assignment.query.filter_by(user_id=u.id).first()
    if not a:
        a = Assignment(user_id=u.id, source="manual", explanation="")
        db.session.add(a)
    before = cal.labels.get(a.period, "none") if a.period else "none"
    after = cal.labels.get(period, "none") if period else "none"
    a.period, a.source, a.rank = period, "manual", None
    rank = next((p.rank for p in u.preferences if p.period == period), None)
    a.rank = rank
    a.explanation = (f"Set by hand by {current_user().email} on {date.today()} "
                     f"(was {before}, now {after})"
                     + (f"; this was the pilot's preference #{rank}." if rank else "."))
    audit(f"moved {u.email} vacation from {before} to {after}")
    db.session.commit()
    flash(f"{u.full_name}: vacation moved from {before} to {after}.", "ok")
    return redirect(url_for("admin.scheduler", group=request.form.get("g", ""),
                            role=request.form.get("r", "")) + f"#u{u.id}")


@bp.route("/scheduler/publish", methods=["POST"])
@admin_required
def publish():
    if service.status() != "draft":
        flash("Run the scheduler first.", "error")
        return redirect(url_for("admin.scheduler"))
    sent = service.publish(current_user().email)
    audit(f"published the schedule ({sent} emails)")
    db.session.commit()
    flash(f"Published. {sent} pilot(s) were emailed"
          + (" (emails are in the Outbox, not sent for real yet)."
             if current_app.config["EMAIL_BACKEND"] == "outbox" else "."), "ok")
    return redirect(url_for("admin.scheduler"))


@bp.route("/scheduler/unpublish", methods=["POST"])
@admin_required
def unpublish():
    if service.status() == "published":
        cfg.set("schedule_status", "draft")
        audit("unpublished the schedule")
        db.session.commit()
        flash("Unpublished. Pilots no longer see their week. Make changes and publish "
              "again; only pilots whose week changed will be emailed.", "ok")
    return redirect(url_for("admin.scheduler"))


@bp.route("/scheduler/reset", methods=["POST"])
@admin_required
def reset():
    """Throw away the draft and reopen rankings."""
    if service.status() == "published":
        flash("Unpublish first.", "error")
        return redirect(url_for("admin.scheduler"))
    Assignment.query.delete()
    cfg.set("schedule_status", "not_run")
    audit("discarded the draft and reopened rankings")
    db.session.commit()
    flash("Draft discarded. Pilots can change their rankings again.", "ok")
    return redirect(url_for("admin.scheduler"))


@bp.route("/scheduler/export.csv")
@admin_required
def export():
    cal = service.calendar()
    by_user = {a.user_id: a for a in Assignment.query.all()}
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["seniority", "last_name", "first_name", "email", "role", "group",
                "hire_date", "vacation_start", "vacation_week", "how", "explanation"])
    for i, u in enumerate(service.pilots(), start=1):
        a = by_user.get(u.id)
        w.writerow([i, u.last_name, u.first_name, u.email, u.role, u.group, u.hire_date,
                    a.period if a else "", cal.labels.get(a.period, "") if a and a.period else "",
                    a.source if a else "", a.explanation if a else ""])
    return Response(out.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": f"attachment; filename=vacation-schedule-{cal.year}.csv"})


# ---------- settings, outbox, test tools ----------

@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings_page():
    if request.method == "POST":
        f = request.form
        try:
            year = int(f["year"])
            start = date.fromisoformat(f["cycle_start"])
            for k in ("cap_pic", "cap_sic", "required_crews"):
                if int(f[k]) < 0:
                    raise ValueError(f"{k} cannot be negative")
            if f.get("ranking_deadline"):
                date.fromisoformat(f["ranking_deadline"])
        except (ValueError, KeyError) as e:
            flash(f"Not saved: {e}", "error")
            return redirect(url_for("admin.settings_page"))
        calendar_changed = (str(year) != cfg.get("year")
                            or start.isoformat() != cfg.get("cycle_start"))
        for k in cfg.EDITABLE:
            cfg.set(k, f.get(k, "").strip())
        audit("changed settings")
        db.session.commit()
        msg = "Settings saved."
        if calendar_changed and Preference.query.count():
            msg += (" The calendar changed, so rankings for dates that are no longer "
                    "duty weeks will be ignored. Ask pilots to check their rankings.")
        flash(msg, "ok")
        return redirect(url_for("admin.settings_page"))
    values = {k: cfg.get(k) for k in cfg.EDITABLE}
    return render_template("admin/settings.html", values=values, meta=cfg.DEFAULTS,
                           cal=service.calendar())


@bp.route("/outbox")
@admin_required
def outbox():
    msgs = EmailMessage.query.order_by(EmailMessage.id.desc()).limit(300).all()
    log = AuditLog.query.order_by(AuditLog.id.desc()).limit(100).all()
    logo = url_for("static", filename="brand/logo-email.png")
    previews = {m.id: emailer.render_html(m.body, logo) for m in msgs}
    return render_template("admin/outbox.html", msgs=msgs, log=log, previews=previews)


@bp.route("/test/fill-preferences", methods=["POST"])
@admin_required
def fill_preferences():
    if not current_app.config["TEST_TOOLS"] or not service.rankings_open():
        flash("Not available now.", "error")
        return redirect(url_for("admin.scheduler"))
    cal = service.calendar()
    n = 0
    rng = random.Random()
    for u in service.pilots():
        if u.prefs_submitted_at:
            continue
        keys = list(cal.by_group.get(u.group, []))
        # Summer and holiday weeks are popular, to make conflicts realistic.
        weights = [3 if k[5:7] in ("06", "07", "08", "12") else 1 for k in keys]
        picked = []
        for _ in range(rng.randint(0, min(8, len(keys)))):
            k = rng.choices(keys, weights)[0]
            if k not in picked:
                picked.append(k)
        service.save_preferences(u, picked)
        n += 1
    audit(f"test tool: filled random preferences for {n} pilots")
    db.session.commit()
    flash(f"Filled random rankings for {n} pilots who had not submitted.", "ok")
    return redirect(url_for("admin.scheduler"))
