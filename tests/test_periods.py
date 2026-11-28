from datetime import date

from app.periods import all_periods, duty_periods


def test_rule3_example():
    a = duty_periods(2027, date(2027, 1, 1), "A")
    assert a[0].start == date(2027, 1, 1) and a[0].end == date(2027, 1, 8)
    assert a[1].start == date(2027, 1, 15)  # off 9-14, back on the 15th


def test_group_b_starts_on_group_a_day_8():
    b = duty_periods(2027, date(2027, 1, 1), "B")
    assert b[0].start == date(2027, 1, 8)  # swap day
    assert b[0].end == date(2027, 1, 15)  # B's Day 8 = A's next Day 1


def test_every_period_starts_inside_the_year():
    for g in "AB":
        ps = duty_periods(2027, date(2026, 6, 3), g)
        assert all(p.start.year == 2027 for p in ps)
        assert 26 <= len(ps) <= 27


def test_cycle_start_before_the_year():
    a = duty_periods(2027, date(2026, 12, 25), "A")
    assert a[0].start == date(2027, 1, 8)


def test_all_periods_sorted():
    ps = all_periods(2027, date(2027, 1, 1))
    assert [p.start for p in ps] == sorted(p.start for p in ps)
