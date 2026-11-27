# Pilot Vacation Scheduler

A website that builds the yearly vacation schedule for Transmedics pilots.
Admins upload the pilot list, pilots rank their duty weeks, and the scheduler
assigns one vacation period per pilot by seniority, following the
*Pilot Scheduling Rules*.

This first version runs **on your own computer**. Nothing is on the internet yet,
and no real emails are sent (they appear on an **Outbox** page instead).
Hosting, company sign-in and real email can be added later without starting over.

---

## Start it on your computer (about 15 minutes the first time)

You only do steps 1 and 2 once.

### Step 1. Install Python

Python is the free program the scheduler runs on.

**Windows**
1. Go to <https://www.python.org/downloads/> and click the yellow **Download Python** button.
2. Open the downloaded file.
3. On the first screen, **tick "Add python.exe to PATH"** at the bottom. This matters.
4. Click **Install Now** and wait until it says "Setup was successful". Close it.

**Mac**
1. Go to <https://www.python.org/downloads/> and click the yellow **Download Python** button.
2. Open the downloaded `.pkg` file and click **Continue** / **Install** until it finishes.

### Step 2. Download the scheduler

The easiest way is **GitHub Desktop**, a free app that also makes updates one click.

1. Download it from <https://desktop.github.com/> and install it.
2. Open it and sign in with your GitHub account.
3. Click **File → Clone repository**, choose **svitozaro/transmedics**, and click **Clone**.
   Note where it saves the folder (usually `Documents/GitHub/transmedics`).
4. Until the pull request is merged, the scheduler lives on a separate branch: at the top of
   GitHub Desktop, click **Current branch** and choose **claude/project-thread-4eztdr**.
   After it is merged, stay on **main**.

### Step 3. Start the scheduler

**Windows:** open the `transmedics` folder and double-click **`start-windows.bat`**.
If Windows shows "Windows protected your PC", click **More info → Run anyway**.

**Mac:**
1. Open the **Terminal** app (press ⌘ + Space, type `Terminal`, press Enter).
2. Type `bash ` (with a space after it), then drag the **`start-mac.command`** file from
   the `transmedics` folder into the Terminal window, and press **Enter**.

The first start takes a minute or two while it sets itself up. Then your browser opens
**<http://127.0.0.1:8000>** by itself. If it does not, open that address yourself.

**Keep the black window open while you use the scheduler.** To stop it, close that window
(or press `Ctrl + C` in it). Start it again the same way next time; your data is kept.

---

## First tour (10 minutes)

1. **Create the admin account.** The first page asks for your name, your
   `@transmedics.com` email and a password. You are the first admin.
2. **Upload pilots.** On **Users**, choose `sample_data/pilots_sample.csv`
   (140 made-up pilots) and click **Upload**. Your real file needs these columns:
   first name, last name, role (PIC or SIC), date of hire, group (A or B), and optionally email.
3. **Invite pilots.** Click **Send invitations**. Open **Outbox** to see the emails
   pilots would get. Each has a personal link to choose a password.
4. **Try the pilot view.** Copy one invitation link, open a **private / incognito browser
   window**, paste the link, choose a password, and drag a few weeks into **My ranking**.
   Click **Submit my ranking**.
5. **Fill the rest for testing.** Back in the admin window, open **Scheduler** and click
   **Test: fill random rankings**. This gives every pilot who has not submitted some random
   choices so you can see a full run.
6. **Run it.** Click **Run the scheduler**. The calendar shows each pilot's rankings
   (blue numbers), weeks they did not rank (orange stripes) and their vacation (green =
   from their ranking, orange **R** = Rule 11, purple **M** = set by hand).
   **Hover over a vacation week** to see why it was assigned.
7. **Adjust if needed.** Click any duty week of a pilot to move their vacation there.
   The rows at the bottom count PICs and SICs off and crews left on duty, and turn red
   when a limit is broken.
8. **Publish.** Click **Publish**. Every pilot gets an email (in the Outbox).
   **Unpublish** lets you change things; when you publish again, only pilots whose week
   changed are emailed.
9. **Settings** holds the year, Group A's first duty day, the PIC/SIC limits, the minimum
   crews on duty, and an optional ranking deadline. It also lists every duty period.

To start over with an empty scheduler, stop it and delete the `instance` folder inside
`transmedics`. (That folder holds the database. Do not delete it once you use real data.)

## Getting updates

When there is a new version: in GitHub Desktop click **Fetch origin**, then **Pull origin**.
Stop the scheduler and start it again.

## If something goes wrong

| What you see | What to do |
|---|---|
| "Python was not found" | Install Python (Step 1). On Windows, reinstall and tick **Add python.exe to PATH**. |
| "Address already in use" | The scheduler is already running in another window. Use that one, or close it first. |
| The page says "Your form expired" | Go back, reload the page, and try again. |
| Forgot the admin password | Click **Forgot your password?**. The reset email appears in the Outbox, which another admin can open. If you are the only admin, open a terminal in the `transmedics` folder and run `.venv/bin/python run.py reset-password you@transmedics.com` (Windows: `.venv\Scripts\python run.py reset-password you@transmedics.com`). It prints a temporary password. |

---

## How the rules are applied

See [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) for how each rule was turned into code,
the defaults chosen for questions that are still open, and how to change them.

## For developers

* Python 3.10+, Flask, SQLAlchemy. Database: SQLite in `instance/scheduler.db`.
* `app/periods.py` (duty calendar) and `app/scheduler.py` (assignment algorithm) are pure
  Python with no web code. Tests: `pip install -r requirements-dev.txt && pytest`.
* Settings for hosting later, all through environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file in `instance/` | e.g. `postgresql+psycopg://user:pass@host/db` |
| `SECRET_KEY` | random, saved in `instance/secret_key` | Signs sign-in cookies. Set it when hosted. |
| `EMAIL_BACKEND` | `outbox` | `smtp` to really send, with `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` |
| `BASE_URL` | `http://127.0.0.1:8000` | Used in links inside emails |
| `ALLOWED_EMAIL_DOMAIN` | `transmedics.com` | Only these addresses can have accounts |
| `TEST_TOOLS` | `1` | Set `0` to hide the "fill random rankings" button |

Sign-in lives in `app/auth.py`; company single sign-on (e.g. Microsoft) can replace the
password pages there without touching the scheduler.
