"""Start the scheduler on this computer: python run.py, then open http://127.0.0.1:8000"""
import os
import sys
import threading
import webbrowser

if sys.version_info < (3, 10):
    sys.exit("This app needs Python 3.10 or newer. Install the latest from https://www.python.org/downloads/")

from app import create_app  # noqa: E402

app = create_app()


def reset_password(email):
    """Emergency: python run.py reset-password someone@transmedics.com"""
    import secrets
    from app.auth import set_password
    from app.models import User, db
    with app.app_context():
        u = User.query.filter_by(email=email.strip().lower()).first()
        if not u:
            sys.exit(f"No account for {email}")
        temp = "-".join(secrets.token_urlsafe(4) for _ in range(3))
        set_password(u, temp, must_change=True)
        u.active = True
        db.session.commit()
        print(f"Temporary password for {u.email}: {temp}  (must be changed at sign-in)")


if __name__ == "__main__" and sys.argv[1:2] == ["reset-password"] and len(sys.argv) == 3:
    reset_password(sys.argv[2])
elif __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    url = f"http://127.0.0.1:{port}"
    print(f"\n  Pilot Vacation Scheduler is running at {url}")
    print("  Keep this window open while you use it. Press Ctrl+C to stop.\n  (A red 'development server' warning below is normal on your own computer.)\n")
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)
