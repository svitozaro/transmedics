from datetime import date

from app.scheduler import PilotIn, crews, run

PERIODS = {"A": ["w1", "w3", "w5", "w7"], "B": ["w2", "w4", "w6", "w8"]}
CAPS = {"PIC": 1, "SIC": 1}


def pilot(i, role, year, prefs=(), group="A"):
    return PilotIn(id=i, name=f"P{i}", role=role, group=group,
                   hire_date=date(year, 1, 1), last_name=f"L{i}", prefs=list(prefs))


def test_rule10_example_from_the_rules():
    # SIC2 (2019) > SIC1 (2020) > PIC1 (2021) > PIC2 (2022). Caps of 1 per role.
    sic2 = pilot(1, "SIC", 2019, ["w1"])
    sic1 = pilot(2, "SIC", 2020, ["w1", "w3"])
    pic1 = pilot(3, "PIC", 2021, ["w1"])
    pic2 = pilot(4, "PIC", 2022, ["w1", "w3"])
    r = run([pic2, sic1, pic1, sic2], PERIODS, CAPS)
    assert (r[1].period, r[1].rank) == ("w1", 1)
    assert (r[2].period, r[2].rank) == ("w3", 2)  # w1 SIC slot taken by SIC2
    assert (r[3].period, r[3].rank) == ("w1", 1)  # role caps are separate
    assert (r[4].period, r[4].rank) == ("w3", 2)


def test_role_does_not_matter_for_order():
    caps = {"PIC": 1, "SIC": 1}
    pic_junior = pilot(1, "PIC", 2020, ["w1"])
    pic_senior = pilot(2, "PIC", 2010, ["w1"])
    r = run([pic_junior, pic_senior], PERIODS, caps)
    assert r[2].period == "w1" and r[1].period != "w1"


def test_rule11_senior_gets_latest_junior_gets_earliest():
    senior = pilot(1, "PIC", 2010)  # no rankings
    junior = pilot(2, "PIC", 2020)
    r = run([junior, senior], PERIODS, CAPS)
    assert r[1].period == "w7" and r[1].source == "rule11"
    assert r[2].period == "w1" and r[2].source == "rule11"


def test_rule11_middle_pilots_alternate_from_both_ends():
    ps = [pilot(i, "PIC", 2000 + i) for i in range(1, 5)]
    r = run(ps, PERIODS, CAPS)
    assert [r[i].period for i in range(1, 5)] == ["w7", "w5", "w3", "w1"]


def test_unmet_preferences_fall_to_rule11():
    a = pilot(1, "PIC", 2010, ["w3"])
    b = pilot(2, "PIC", 2011, ["w3"])
    r = run([a, b], PERIODS, CAPS)
    assert r[1].period == "w3"
    assert r[2].source == "rule11" and r[2].period == "w7"
    assert "PIC limit reached" in r[2].explanation


def test_only_own_group_weeks():
    p = pilot(1, "PIC", 2010, ["w2", "w3"])  # w2 is a Group B week
    r = run([p], PERIODS, CAPS)
    assert r[1].period == "w3" and r[1].rank == 2


def test_nobody_placed_when_everything_is_full():
    ps = [pilot(i, "SIC", 2000 + i) for i in range(1, 6)]  # 4 weeks, cap 1
    r = run(ps, PERIODS, CAPS)
    assert sum(1 for x in r.values() if x.period) == 4
    assert [x.source for x in r.values()].count("none") == 1


def test_crews_formula():
    assert crews(3, 6) == 3
    assert crews(1, 6) == 1  # only one PIC
    assert crews(5, 5) == 2  # 2-PIC crews


def test_crew_check_blocks_a_week():
    # Group A: 2 PICs + 2 SICs = 2 crews. Require 2 crews: nobody can be off.
    caps = {"PIC": 3, "SIC": 3}
    ps = [pilot(1, "PIC", 2001, ["w1"]), pilot(2, "PIC", 2002),
          pilot(3, "SIC", 2003, ["w1"]), pilot(4, "SIC", 2004)]
    r = run(ps, PERIODS, caps, required_crews=2)
    assert all(x.source == "none" for x in r.values())
    assert "crew minimum" in r[1].explanation
    # Require 1 crew: two pilots can be off in the same week only if a crew remains.
    r = run(ps, PERIODS, caps, required_crews=1)
    assert r[1].period == "w1" and r[3].period == "w1"


def test_each_pilot_gets_one_week_at_most_caps():
    ps = [pilot(i, "PIC" if i % 2 else "SIC", 1990 + i, ["w5", "w1"]) for i in range(1, 9)]
    caps = {"PIC": 2, "SIC": 2}
    r = run(ps, PERIODS, caps)
    per = {}
    for p in ps:
        per.setdefault((r[p.id].period, p.role), 0)
        per[(r[p.id].period, p.role)] += 1
    assert all(n <= 2 for n in per.values())
    assert all(x.period for x in r.values())
