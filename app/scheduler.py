"""The vacation assignment algorithm (Rules 9-12).

This module has no database or web code, so it can be tested on its own.

Step 1, preferences (Rule 10): pilots go one at a time in seniority order
(earliest date of hire first, role ignored). Each pilot gets their highest
ranked duty period that is still available.

Step 2, Rule 11: pilots who got nothing are sorted by seniority. The most
senior remaining pilot gets the latest available period in the year, then the
most junior remaining pilot gets the earliest available period, then the next
most senior gets the latest, and so on, working in from both ends.
ASSUMPTION: the alternating "both ends" order for the pilots in the middle.

A period is "available" for a pilot when both limits hold (Rule 12 plus the
crew check agreed in review):
  * fewer than cap[role] pilots of that role are already off that period, and
  * after this pilot goes off, the pilots still on duty in that group can form
    at least `required_crews` crews. A crew is PIC+SIC or PIC+PIC, so
    crews = min(PICs on duty, floor(all pilots on duty / 2)).
    required_crews = 0 switches the crew check off.
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class PilotIn:
    id: int
    name: str
    role: str  # "PIC" or "SIC"
    group: str  # "A" or "B"
    hire_date: date
    last_name: str = ""
    first_name: str = ""
    prefs: list[str] = field(default_factory=list)  # period keys, rank 1 first


@dataclass
class Result:
    pilot_id: int
    period: str | None
    source: str  # "preference", "rule11" or "none"
    rank: int | None
    explanation: str


def seniority_key(p: PilotIn):
    # ASSUMPTION: equal hire dates are broken by last name, then first name.
    return (p.hire_date, p.last_name.lower(), p.first_name.lower(), p.id)


def crews(pics: int, total: int) -> int:
    return max(0, min(pics, total // 2))


class Board:
    """Keeps count of who is off in each period and checks the limits."""

    def __init__(self, pilots, periods_by_group, caps, required_crews):
        self.caps = caps
        self.required = required_crews
        self.periods_by_group = periods_by_group
        self.group_pic = {g: 0 for g in periods_by_group}
        self.group_all = {g: 0 for g in periods_by_group}
        for p in pilots:
            self.group_all[p.group] = self.group_all.get(p.group, 0) + 1
            if p.role == "PIC":
                self.group_pic[p.group] = self.group_pic.get(p.group, 0) + 1
        self.off = {}  # period key -> {"PIC": n, "SIC": n}

    def counts(self, period):
        return self.off.setdefault(period, {"PIC": 0, "SIC": 0})

    def blocker(self, p: PilotIn, period: str) -> str | None:
        """Why this pilot cannot take this period, or None if they can."""
        if period not in self.periods_by_group.get(p.group, ()):
            return f"not a Group {p.group} duty period"
        c = self.counts(period)
        cap = self.caps[p.role]
        if c[p.role] >= cap:
            return f"{p.role} limit reached ({c[p.role]} of {cap} already off)"
        if self.required > 0:
            pics_on = self.group_pic[p.group] - c["PIC"] - (1 if p.role == "PIC" else 0)
            all_on = self.group_all[p.group] - c["PIC"] - c["SIC"] - 1
            n = crews(pics_on, all_on)
            if n < self.required:
                return (f"crew minimum: only {n} crews would remain on duty, "
                        f"{self.required} needed")
        return None

    def take(self, p: PilotIn, period: str):
        self.counts(period)[p.role] += 1


def run(pilots, periods_by_group, caps, required_crews=0, labels=None):
    """Assign one vacation period to each pilot.

    periods_by_group: {"A": [period keys in date order], "B": [...]}
    caps: {"PIC": 3, "SIC": 3}
    labels: optional {period key: "Jan 1-8"} used in explanations.
    Returns {pilot id: Result}.
    """
    labels = labels or {}
    lab = lambda k: labels.get(k, k)
    board = Board(pilots, periods_by_group, caps, required_crews)
    order = sorted(pilots, key=seniority_key)
    total = len(order)
    seniority = {p.id: i + 1 for i, p in enumerate(order)}
    results: dict[int, Result] = {}
    skipped: dict[int, list[str]] = {}

    def who(p):
        return (f"Seniority #{seniority[p.id]} of {total} "
                f"(hired {p.hire_date.isoformat()}, {p.role}, Group {p.group}).")

    # Step 1: preferences, in seniority order.
    for p in order:
        notes = []
        for rank, period in enumerate(p.prefs, start=1):
            why = board.blocker(p, period)
            if why is None:
                board.take(p, period)
                text = f"{who(p)} Got preference #{rank} ({lab(period)})."
                if notes:
                    text += " Higher choices were full: " + "; ".join(notes) + "."
                results[p.id] = Result(p.id, period, "preference", rank, text)
                break
            notes.append(f"#{rank} {lab(period)}: {why}")
        else:
            skipped[p.id] = notes

    # Step 2: Rule 11 for everyone left, working in from both ends.
    remaining = [p for p in order if p.id not in results]
    lo, hi, senior_turn = 0, len(remaining) - 1, True
    while lo <= hi:
        p = remaining[lo] if senior_turn else remaining[hi]
        periods = board.periods_by_group.get(p.group, [])
        candidates = list(reversed(periods)) if senior_turn else list(periods)
        pick = next((k for k in candidates if board.blocker(p, k) is None), None)
        if p.prefs:
            reason = (f"None of the {len(p.prefs)} ranked weeks were available ("
                      + "; ".join(skipped.get(p.id, [])) + ").")
        else:
            reason = "Did not rank any weeks."
        side = ("most senior" if senior_turn else "most junior")
        if pick:
            board.take(p, pick)
            where = "latest" if senior_turn else "earliest"
            text = (f"{who(p)} {reason} Rule 11: {side} of the pilots still "
                    f"without a week, so given the {where} available Group "
                    f"{p.group} week ({lab(pick)}).")
            results[p.id] = Result(p.id, pick, "rule11", None, text)
        else:
            text = (f"{who(p)} {reason} Rule 11 found no available Group "
                    f"{p.group} week: every week is at its limit. An admin "
                    "must assign this pilot by hand.")
            results[p.id] = Result(p.id, None, "none", None, text)
        if senior_turn:
            lo += 1
        else:
            hi -= 1
        senior_turn = not senior_turn

    return results
