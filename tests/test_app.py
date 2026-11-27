import re
from pathlib import Path

import pytest

from app import create_app
from app.models import Assignment, EmailMessage, User, db

SAMPLE = Path(__file__).parent.parent / "sample_data" / "pilots_sample.csv"


@pytest.fixture
def client(tmp_path):
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 't.db'}",
                      "TESTING": True})
    with app.test_client() as c:
        c.app = app
        yield c


def csrf(c, path):
    html = c.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def post(c, path, data, page=None, **kw):
    data = dict(data, csrf=csrf(c, page or path))
    return c.post(path, data=data, follow_redirects=True, **kw)


def make_admin(c):
    return post(c, "/setup", dict(first_name="Ada", last_name="Admin",
                                  email="ada@transmedics.com",
                                  password="LongEnough123", confirm="LongEnough123"))


def test_post_without_csrf_is_refused(client):
    assert client.post("/login", data={"email": "x"}).status_code == 400


def test_full_flow(client):
    assert client.get("/").headers["Location"].endswith("/setup")
    assert b"Upload the pilot list" in make_admin(client).data

    with open(SAMPLE, "rb") as fh:
        r = post(client, "/admin/users/import", {"file": (fh, "p.csv")}, page="/admin/users",
                 content_type="multipart/form-data")
    assert b"Imported 140 pilots" in r.data

    r = post(client, "/admin/users/invite-all", {}, page="/admin/users")
    assert b"Sent 140 invitation" in r.data

    # A pilot accepts the invitation from the outbox.
    with client.app.app_context():
        pilot = User.query.filter_by(role="PIC", group="A").first()
        email = pilot.email
        msg = EmailMessage.query.filter_by(to=email).first()
        link = re.search(r"http://127.0.0.1:8000(\S+)", msg.body).group(1)
    post(client, "/logout", {}, page="/admin/users")
    r = post(client, link, dict(password="PilotPass123", confirm="PilotPass123"))
    assert b"Drag your duty weeks" in r.data
    weeks = re.findall(r'data-key="([\d-]+)"', r.get_data(as_text=True))
    r = post(client, "/pilot/", {"ranked": [weeks[5], weeks[2]]})
    assert b"You ranked 2 week(s)" in r.data

    # Admin fills the rest, runs, publishes.
    post(client, "/logout", {}, page="/pilot/")
    post(client, "/login", dict(email="ada@transmedics.com", password="LongEnough123"))
    post(client, "/admin/test/fill-preferences", {}, page="/admin/scheduler")
    r = post(client, "/admin/scheduler/run", {}, page="/admin/scheduler")
    assert b"Scheduler finished" in r.data
    with client.app.app_context():
        a = Assignment.query.filter_by(user_id=pilot.id).first()
        assert a.period == weeks[5] and a.rank == 1
        assert Assignment.query.filter(Assignment.period.isnot(None)).count() == 140
    r = post(client, "/admin/scheduler/publish", {}, page="/admin/scheduler")
    assert b"Published. 140 pilot(s) were emailed" in r.data

    # Unpublish, move one pilot, republish: only that pilot is emailed.
    post(client, "/admin/scheduler/unpublish", {}, page="/admin/scheduler")
    r = post(client, "/admin/scheduler/assign", {"user_id": pilot.id, "period": weeks[2]},
             page="/admin/scheduler")
    assert b"vacation moved" in r.data
    r = post(client, "/admin/scheduler/publish", {}, page="/admin/scheduler")
    assert b"Published. 1 pilot(s) were emailed" in r.data
    with client.app.app_context():
        last = EmailMessage.query.order_by(EmailMessage.id.desc()).first()
        assert last.to == email and "changed" in last.body

    assert client.get("/admin/scheduler/export.csv").status_code == 200


def test_temp_password_forces_change(client):
    make_admin(client)
    post(client, "/admin/users/new", dict(first_name="Pat", last_name="Pilot",
         email="pat@transmedics.com", role="SIC", group="B", hire_date="2020-02-02"),
         page="/admin/users")
    with client.app.app_context():
        uid = User.query.filter_by(email="pat@transmedics.com").one().id
    r = post(client, f"/admin/users/{uid}/temp-password", {}, page=f"/admin/users/{uid}")
    temp = re.search(r"Temporary password for pat@transmedics.com: (\S+)",
                     r.get_data(as_text=True)).group(1)
    post(client, "/logout", {}, page="/admin/users")
    r = post(client, "/login", dict(email="pat@transmedics.com", password=temp))
    assert b"Choose your own password" in r.data
    assert client.get("/pilot/").headers["Location"].endswith("/change-password")


def test_bad_csv_imports_nothing(client):
    make_admin(client)
    import io
    data = b"first name,last name,role,date of hire,group\nA,B,PIC,2020-01-01,A\nC,D,XX,2020-01-01,A\n"
    r = post(client, "/admin/users/import", {"file": (io.BytesIO(data), "p.csv")},
             page="/admin/users", content_type="multipart/form-data")
    assert b"Nothing was imported" in r.data and b"Row 3" in r.data
    with client.app.app_context():
        assert User.query.count() == 1


def test_sample_button_and_codespaces_links(client, monkeypatch):
    make_admin(client)
    r = post(client, "/admin/users/import", {"sample": "1"}, page="/admin/users")
    assert b"Imported 140 pilots" in r.data
    monkeypatch.setenv("CODESPACE_NAME", "demo")
    monkeypatch.setenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    from app import _default_base_url
    assert _default_base_url() == "https://demo-8000.app.github.dev"
