"""Glue between the database and the pure scheduler/period code."""
from dataclasses import dataclass
from datetime import date

from . import emailer, scheduler
from . import settings as cfg
from .models import Assignment, Preference, PublishedAssignment, User, db, now
from .periods import Period, all_periods


@dataclass
class Calendar:
    year: int
    periods: list[Period]  # both groups, date order
    by_group: dict[str, list[str]]
    labels: dict[str, str]
    group_of: dict[str, str]


def calendar() -> Calendar:
    year = cfg.get_int("year")
    start = cfg.get_date("cycle_start") or date(year, 1, 1)
    periods = all_periods(year, start)
    return Calendar(
        year=year, periods=periods,
        by_group={g: [p.key for p in periods if p.group == g] for g in "AB"},
        labels={p.key: p.label() for p in periods},
        group_of={p.key: p.group for p in periods})


def pilots():
    q = User.query.filter(User.role.in_(["PIC", "SIC"]), User.active.is_(True))
    return sorted(q.all(), key=lambda u: scheduler.seniority_key(to_pilot_in(u)))


def to_pilot_in(u, prefs=None):
    return scheduler.PilotIn(
        id=u.id, name=u.full_name, role=u.role, group=u.group or "A",
        hire_date=u.hire_date or date.max, last_name=u.last_name,
        first_name=u.first_name, prefs=prefs or [])


def status():
    return cfg.get("schedule_status")


def rankings_open():
    if status() != "not_run":
        return False
    deadline = cfg.get_date("ranking_deadline")
    return not deadline or date.today() <= deadline


def caps():
    return {"PIC": cfg.get_int("cap_pic"), "SIC": cfg.get_int("cap_sic")}


def run_scheduler():
    cal = calendar()
    ps = pilots()
    inputs = []
    for u in ps:
        valid = set(cal.by_group.get(u.group, []))
        prefs = [p.period for p in u.preferences if p.period in valid]
        inputs.append(to_pilot_in(u, prefs))
    results = scheduler.run(inputs, cal.by_group, caps(),
                            cfg.get_int("required_crews"), cal.labels)
    Assignment.query.delete()
    for r in results.values():
        db.session.add(Assignment(user_id=r.pilot_id, period=r.period,
                                  source=r.source, rank=r.rank, explanation=r.explanation))
    cfg.set("schedule_status", "draft")
    cfg.set("last_run_at", now().isoformat(timespec="seconds"))
    return results


def period_counts(assignments, people):
    """{period: {"PIC": n, "SIC": n}} from the current draft."""
    role = {u.id: u.role for u in people}
    out = {}
    for a in assignments:
        if a.period and a.user_id in role:
            out.setdefault(a.period, {"PIC": 0, "SIC": 0})[role[a.user_id]] += 1
    return out


def crews_left(group, period, counts, people):
    pics = sum(1 for u in people if u.group == group and u.role == "PIC")
    total = sum(1 for u in people if u.group == group)
    c = counts.get(period, {"PIC": 0, "SIC": 0})
    return scheduler.crews(pics - c["PIC"], total - c["PIC"] - c["SIC"])


def problems(cal, assignments, people):
    """Plain-language warnings about the draft, e.g. after manual edits."""
    out = []
    counts = period_counts(assignments, people)
    cp, need = caps(), cfg.get_int("required_crews")
    for key, c in counts.items():
        for r in ("PIC", "SIC"):
            if c[r] > cp[r]:
                out.append(f"{cal.labels.get(key, key)}: {c[r]} {r}s off, limit is {cp[r]}.")
        g = cal.group_of.get(key)
        if need and g and crews_left(g, key, counts, people) < need:
            out.append(f"{cal.labels.get(key, key)}: fewer than {need} crews left on duty.")
    have = {a.user_id for a in assignments if a.period}
    missing = [u for u in people if u.id not in have]
    if missing and assignments:
        out.append(f"{len(missing)} pilot(s) have no vacation week: "
                   + ", ".join(u.full_name for u in missing[:10])
                   + ("..." if len(missing) > 10 else ""))
    return out


def publish(actor_email):
    """Mark published and email pilots. Returns the number of emails."""
    cal = calendar()
    first_time = PublishedAssignment.query.count() == 0
    old = {p.user_id: p.period for p in PublishedAssignment.query.all()}
    sent = 0
    for a in Assignment.query.all():
        u = a.user
        if not u.active or not u.is_pilot:
            continue
        new_label = cal.labels.get(a.period, "not assigned yet") if a.period else "not assigned yet"
        if first_time or u.id not in old:
            emailer.send(u.email, f"Your {cal.year} vacation week",
                         f"Hello {u.first_name},\n\nThe {cal.year} pilot vacation schedule "
                         f"has been published.\n\nYour vacation week: {new_label}\n\n"
                         "You can also see it in the vacation portal.")
            sent += 1
        elif old[u.id] != a.period:
            was = cal.labels.get(old[u.id], "none") if old[u.id] else "none"
            emailer.send(u.email, f"Change to your {cal.year} vacation week",
                         f"Hello {u.first_name},\n\nThe {cal.year} pilot vacation schedule "
                         f"was updated and your vacation week has changed.\n\n"
                         f"Previous vacation week: {was}\nNew vacation week: {new_label}\n")
            sent += 1
    PublishedAssignment.query.delete()
    for a in Assignment.query.all():
        db.session.add(PublishedAssignment(user_id=a.user_id, period=a.period))
    cfg.set("schedule_status", "published")
    cfg.set("last_published_at", now().isoformat(timespec="seconds"))
    return sent


def save_preferences(user, keys):
    valid = set(calendar().by_group.get(user.group, []))
    seen, clean = set(), []
    for k in keys:
        if k in valid and k not in seen:
            seen.add(k)
            clean.append(k)
    Preference.query.filter_by(user_id=user.id).delete()
    for i, k in enumerate(clean, start=1):
        db.session.add(Preference(user_id=user.id, period=k, rank=i))
    user.prefs_submitted_at = now()
    return clean
