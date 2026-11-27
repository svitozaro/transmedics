"""Read the pilot list CSV (structure items 10-11).

Required columns: first name, last name, role (PIC or SIC), date of hire,
group (A or B). Optional column: email.
ASSUMPTION: if there is no email column, the email is built as
firstname.lastname@<company domain>. Rows are matched to existing accounts by email.
Column names are matched loosely ("First Name", "first_name", "Date of hire" ...).
"""
import csv
import io
import re
from datetime import date, datetime

ALIASES = {
    "first_name": {"first_name", "firstname", "first", "given_name"},
    "last_name": {"last_name", "lastname", "last", "surname", "family_name"},
    "role": {"role", "position", "seat"},
    "hire_date": {"hire_date", "date_of_hire", "start_date", "hired", "doh", "hiredate"},
    "group": {"group", "crew_group", "team"},
    "email": {"email", "e_mail", "email_address", "username"},
}
REQUIRED = ["first_name", "last_name", "role", "hire_date", "group"]
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%b %d, %Y", "%Y/%m/%d"]


def _norm(h):
    return re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower()).strip("_")


def parse_date(text) -> date:
    text = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"date '{text}' not understood (use YYYY-MM-DD or MM/DD/YYYY)")


def make_email(first, last, domain):
    clean = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())
    return f"{clean(first)}.{clean(last)}@{domain}"


def parse(raw: bytes, domain: str):
    """Returns (rows, errors). rows are dicts ready to save."""
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    colmap = {}
    for h in reader.fieldnames or []:
        for field, names in ALIASES.items():
            if _norm(h) in names and field not in colmap:
                colmap[field] = h
    missing = [f.replace("_", " ") for f in REQUIRED if f not in colmap]
    if missing:
        return [], [f"Missing column(s): {', '.join(missing)}. Found: "
                    f"{', '.join(reader.fieldnames or []) or 'nothing'}."]
    rows, errors, seen = [], [], set()
    for n, r in enumerate(reader, start=2):  # row 1 is the header
        get = lambda f: (r.get(colmap[f]) or "").strip() if f in colmap else ""
        if not any((v or "").strip() for v in r.values() if isinstance(v, str)):
            continue
        try:
            first, last = get("first_name"), get("last_name")
            if not first or not last:
                raise ValueError("first and last name are required")
            role = get("role").upper()
            if role not in ("PIC", "SIC"):
                raise ValueError(f"role must be PIC or SIC, not '{get('role')}'")
            group = get("group").upper().replace("GROUP", "").strip()
            if group not in ("A", "B"):
                raise ValueError(f"group must be A or B, not '{get('group')}'")
            email = get("email").lower() or make_email(first, last, domain)
            if not email.endswith("@" + domain):
                raise ValueError(f"email {email} is not an @{domain} address")
            if email in seen:
                raise ValueError(f"email {email} appears twice in the file")
            seen.add(email)
            rows.append(dict(first_name=first, last_name=last, role=role, group=group,
                             hire_date=parse_date(get("hire_date")), email=email))
        except ValueError as e:
            errors.append(f"Row {n}: {e}")
    return rows, errors
