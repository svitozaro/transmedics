"""Duty-period calendar (Rules 3-7).

Every pilot works 8 days on and 6 days off, a 14-day cycle.
Group A's Day 1 is the "cycle start date" setting. Group B starts 7 days
later, so Group A's Day 8 is Group B's Day 1 (the swap day), and Group B's
Day 8 is Group A's next Day 1. That gives 2 overlap days per cycle.

A duty period is identified by its group and its first day.
ASSUMPTION: a duty period belongs to the year in which it starts, so a
period that starts on 28 Dec and ends in January counts for the earlier year.
"""
from dataclasses import dataclass
from datetime import date, timedelta

CYCLE_DAYS = 14
DUTY_DAYS = 8
GROUP_OFFSET = {"A": 0, "B": 7}


@dataclass(frozen=True)
class Period:
    group: str
    start: date

    @property
    def end(self) -> date:
        return self.start + timedelta(days=DUTY_DAYS - 1)

    @property
    def key(self) -> str:
        return self.start.isoformat()

    def label(self) -> str:
        if self.start.month == self.end.month:
            return f"{self.start:%b} {self.start.day}-{self.end.day}"
        return f"{self.start:%b} {self.start.day} - {self.end:%b} {self.end.day}"


def duty_periods(year: int, cycle_start: date, group: str) -> list[Period]:
    """All duty periods for a group that start inside the calendar year."""
    first = cycle_start + timedelta(days=GROUP_OFFSET[group])
    year_start, year_end = date(year, 1, 1), date(year, 12, 31)
    # Move back or forward to the first period start on or after 1 Jan.
    delta = (year_start - first).days
    steps = -(-delta // CYCLE_DAYS)  # ceiling division, works for negatives
    d = first + timedelta(days=steps * CYCLE_DAYS)
    out = []
    while d <= year_end:
        out.append(Period(group, d))
        d += timedelta(days=CYCLE_DAYS)
    return out


def all_periods(year: int, cycle_start: date) -> list[Period]:
    """Both groups' periods, in date order."""
    return sorted(
        duty_periods(year, cycle_start, "A") + duty_periods(year, cycle_start, "B"),
        key=lambda p: p.start,
    )
