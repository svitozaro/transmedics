# How the rules are applied, and what is assumed

Items marked **ASSUMPTION** are defaults chosen while the question is still open.
Most can be changed on the **Settings** page; the rest are one small code change.

## Decided with you

| Topic | How it works |
|---|---|
| Duty cycle (Rules 3, 5, 6) | 14-day cycle, 8 days on. Group A's Day 1 is the **Group A first duty day** setting (e.g. 1 Jan: on Jan 1-8, off 9-14, back Jan 15). Group B's Day 1 is Group A's Day 8 (the swap day), and Group B's Day 8 is Group A's next Day 1, so there are 2 overlap days per cycle. |
| What a pilot can rank (Rule 7) | Only their own group's 8-day duty periods. |
| Picking order (Rule 10) | One pilot at a time by date of hire, earliest first, role ignored. Each gets their highest-ranked period that is still open. |
| Rule 11 | The most senior pilot still without a week gets the **latest** open period of their group; the most junior gets the **earliest**. |
| Limits (Rule 12 + crew check) | A period is full for a role when **Max PICs** / **Max SICs** are already off (default 3 + 3). Also, after a pilot goes off, the pilots still on duty in that group must form at least **Minimum crews** crews, where crews = min(PICs on duty, all on duty ÷ 2, rounded down), because a crew is PIC+SIC or 2 PICs. |
| Typos | 70 PICs **and 70 SICs**; "Group 8" means **Group B**; example dates follow Rule 3. |

## Assumptions (still open)

1. **Minimum crews on duty defaults to 0 (check off)** until the real number is known. Set it on Settings.
2. **Rule 11 for pilots in the middle:** after the most senior and most junior, it alternates: next most senior gets the latest open period, next most junior the earliest, working inwards.
3. **Equal hire dates** are ordered by last name, then first name.
4. **A duty period belongs to the year it starts in.** A period starting 28 Dec counts for that year even though it ends in January.
5. **Rankings lock when the scheduler runs.** Admins can click "Discard draft and reopen rankings" to unlock. An optional **ranking deadline** also closes them.
6. **Pilots with no possible week:** if every period of their group is full, they are flagged "could not be placed" and the admin assigns them by hand. Manual changes may break a limit; the page lists any broken limits in red before you publish.
7. **CSV email column:** optional. Without it the email is `firstname.lastname@transmedics.com`. Re-uploading updates pilots with the same email instead of making duplicates. If any row has an error, nothing is imported.
8. **Pilots see only their own result**, and only after publishing. The "why" explanations are for admins.
9. **Changing the year or Group A's first day** after pilots have ranked: rankings for dates that are no longer duty periods are ignored, and the admin is warned.
10. **Inactive pilots** (untick "Active" on the user page) are left out of the schedule but kept in the system.

## Changes from the tool structure document (security)

* **No shared default password** (items 5-6). A shared password that everyone knows would let anyone sign in as any pilot until they changed it. Instead each person gets their own one-time link by email to choose a password. Admins can also create a **temporary password** for one person; it is shown once and must be changed at first sign-in, which keeps the spirit of item 6.
* **Passwords are not shown** on the user page (item 9). They are stored scrambled (hashed) so that nobody, including admins and anyone who gets a copy of the database, can read them. The page shows whether a password is set instead.
* **Forgot password** sends a reset link valid for 24 hours. Invitation links are valid for 14 days.

## Not built yet

* Real email sending is ready but switched off (`EMAIL_BACKEND=smtp` turns it on once an email service is chosen).
* Hosting, company single sign-on and a domain.
* Limits on repeated wrong passwords, needed before going on the internet.
