# TransMedics Aviation: Pilot Vacation Portal

A website that builds the yearly vacation schedule for TransMedics Aviation pilots.
Admins upload the pilot list, pilots rank their duty weeks, and the scheduler
assigns one vacation period per pilot by seniority, following the
*Pilot Scheduling Rules*.

This first version is a test version. No real emails are sent (they appear on an
**Outbox** page instead). Hosting, company sign-in and real email can be added later
without starting over.

---

## Start it in your browser with GitHub Codespaces (nothing to install)

Codespaces runs the scheduler on a computer that GitHub provides, and you use it in your
web browser. You only need your GitHub account. Personal GitHub accounts include free
Codespaces hours each month, which is plenty for testing.

### The first time (about 5 minutes)

1. Open <https://github.com/svitozaro/transmedics> and sign in.
2. **Pick the right version.** Until the pull request is merged, the scheduler is on a
   separate branch. Click the branch button near the top left (it says **main**) and choose
   **claude/project-thread-4eztdr**. Once the pull request is merged, leave it on **main**.
3. Click the green **<> Code** button, then the **Codespaces** tab.
4. Click **Create codespace on claude/project-thread-4eztdr** (or **on main** after merging).
5. A new tab opens with an editor and a progress message. **Wait 2 to 4 minutes** the first
   time while it sets itself up. You do not need to type anything.
6. When it is ready, a panel at the bottom shows
   `Pilot Vacation Scheduler is running at ...`, and the scheduler opens in **another
   browser tab** by itself.
   * If no tab opened (your browser may block pop-ups), look for a small message at the
     bottom right saying **"Your application running on port 8000 is available"** and click
     **Open in Browser**.
   * Or click the **Ports** tab in the bottom panel, find **Scheduler (8000)**, and click
     the globe icon next to its address.
7. You now see the scheduler's welcome page. Continue with the **First tour** below.

Keep the editor tab open while you use the scheduler (it can stay in the background).
The address of your scheduler tab is private to your GitHub account, so you can bookmark it.

### Coming back later

Go to <https://github.com/codespaces>, click your codespace, and wait for it to start.
The scheduler starts again by itself and your data (accounts, rankings, schedule) is still
there. If no tab opens, use the **Ports** tab as in step 6.

Codespaces stop by themselves after 30 minutes of not being used, which is fine: just open
it again. GitHub **deletes a codespace that has not been opened for 30 days**, including its
test data, so treat this as a place for testing, not for the real schedule.

### Getting updates

When there is a new version, the simplest way is to create a new codespace (steps 1-6).
Delete the old one at <https://github.com/codespaces> (click **...** then **Delete**).

<details>
<summary><strong>Alternative: run it on your own computer</strong> (needs Python installed)</summary>

1. Install Python from <https://www.python.org/downloads/> (on Windows, tick
   **"Add python.exe to PATH"** on the first screen of the installer).
2. Download the code with GitHub Desktop (<https://desktop.github.com/>):
   **File → Clone repository → svitozaro/transmedics**.
3. Windows: double-click **`start-windows.bat`**. Mac: open **Terminal**, type `bash `,
   drag **`start-mac.command`** into the window, press Enter.
4. Your browser opens **<http://127.0.0.1:8000>**. Keep the black window open while you use it.

</details>

---

## First tour (10 minutes)

1. **Create the admin account.** The first page asks for your name, your
   `@transmedics.com` email and a password. You are the first admin.
2. **Load pilots.** On **Users**, click **Test: load 140 sample pilots**. This loads a
   made-up list (`sample_data/pilots_sample.csv`) so you can try everything. For your real
   list, use **Choose File** and **Upload** instead. It needs these columns: first name,
   last name, role (PIC or SIC), date of hire, group (A or B), and optionally email.
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

To start over with an empty scheduler, delete the `instance` folder (in Codespaces:
right-click it in the file list on the left and choose **Delete**), then restart the
scheduler. That folder holds the database.

## If something goes wrong

| What you see | What to do |
|---|---|
| "Python was not found" | Install Python (Step 1). On Windows, reinstall and tick **Add python.exe to PATH**. |
| "Address already in use" | The scheduler is already running (for example in another editor tab). Use that one. |
| Codespaces: the scheduler stopped or the page does not load | In the editor tab, click the **Terminal** panel at the bottom, type `python run.py` and press Enter. Then open it from the **Ports** tab. |
| The page says "Your form expired" | Go back, reload the page, and try again. |
| Forgot the admin password | Click **Forgot your password?**. The reset email appears in the Outbox, which another admin can open. If you are the only admin, open a terminal (in Codespaces: the **Terminal** panel) and run `python run.py reset-password you@transmedics.com` (on your own Mac: `.venv/bin/python run.py ...`; Windows: `.venv\Scripts\python run.py reset-password you@transmedics.com`). It prints a temporary password. |

---

## Branding

* **Logo:** the official TransMedics logo is in `app/static/brand/logo.svg` (cropped to the
  artwork) and `logo-email.png` (used in emails, since most email programs cannot show SVG).
  To change it, replace those files.
* **Brand red:** `#8b2434`, taken from the logo file. It is set once as `--brand` near the
  top of `app/static/style.css`, and as `BRAND_RED` in `app/emailer.py`.
* Emails start with "TransMedics Aviation:", carry the logo and a TransMedics Aviation
  footer, and also include a plain-text version.

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
