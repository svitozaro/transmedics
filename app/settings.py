"""Admin-editable settings, stored in the database, with defaults."""
from datetime import date

from .models import Setting, db

# key: (default, label, help). Defaults marked ASSUMPTION are placeholders.
DEFAULTS = {
    "year": (str(date.today().year + 1), "Schedule year",
             "The calendar year being scheduled."),
    "cycle_start": (f"{date.today().year + 1}-01-01", "Group A first duty day",
                    "Group A's Day 1 of a 14-day cycle. Group B starts 7 days later "
                    "(Group A's Day 8 is Group B's Day 1)."),
    "cap_pic": ("3", "Max PICs on vacation per week", "Rule 12. Default 3."),
    "cap_sic": ("3", "Max SICs on vacation per week", "Rule 12. Default 3."),
    "required_crews": ("0", "Minimum crews that must stay on duty",
                       "Crew check. A crew is PIC+SIC or 2 PICs. 0 turns the check off. "
                       "ASSUMPTION: the real number is not decided yet."),
    "ranking_deadline": ("", "Ranking deadline (optional)",
                         "Last day pilots can submit rankings, YYYY-MM-DD. Leave empty for "
                         "no deadline. Rankings always lock once the scheduler runs."),
    "schedule_status": ("not_run", None, None),  # not_run, draft, published
    "last_run_at": ("", None, None),
    "last_published_at": ("", None, None),
}

EDITABLE = [k for k, v in DEFAULTS.items() if v[1]]


def get(key):
    row = db.session.get(Setting, key)
    return row.value if row else DEFAULTS[key][0]


def set(key, value):
    row = db.session.get(Setting, key)
    if row:
        row.value = str(value)
    else:
        db.session.add(Setting(key=key, value=str(value)))


def get_int(key):
    try:
        return int(get(key))
    except ValueError:
        return int(DEFAULTS[key][0])


def get_date(key):
    v = get(key)
    return date.fromisoformat(v) if v else None
