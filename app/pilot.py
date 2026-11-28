from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import service
from . import settings as cfg
from .auth import current_user, pilot_required
from .models import PublishedAssignment, db

bp = Blueprint("pilot", __name__, url_prefix="/pilot")


@bp.route("/", methods=["GET", "POST"])
@pilot_required
def ranking():
    u = current_user()
    cal = service.calendar()
    is_open = service.rankings_open()
    if request.method == "POST":
        if not is_open:
            flash("Rankings are closed, so your list was not changed.", "error")
        else:
            saved = service.save_preferences(u, request.form.getlist("ranked"))
            db.session.commit()
            flash(f"Submitted. You ranked {len(saved)} week(s). You can change and "
                  "resubmit until the schedule is run.", "ok")
        return redirect(url_for("pilot.ranking"))
    mine = [p for p in cal.periods if p.group == u.group]
    ranked_keys = [p.period for p in u.preferences]
    by_key = {p.key: p for p in mine}
    ranked = [by_key[k] for k in ranked_keys if k in by_key]
    unranked = [p for p in mine if p.key not in set(ranked_keys)]
    vacation = None
    if service.status() == "published":
        pa = PublishedAssignment.query.filter_by(user_id=u.id).first()
        vacation = cal.labels.get(pa.period) if pa and pa.period else "not assigned"
    return render_template("pilot/ranking.html", u=u, cal=cal, ranked=ranked,
                           unranked=unranked, is_open=is_open, vacation=vacation,
                           deadline=cfg.get("ranking_deadline"))
