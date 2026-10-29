# ShareSpace — Resource Sharing Platform

A functional hackathon prototype for sharing underused college/community spaces and equipment with booking approvals, eligibility verification, check-in/out, condition records, incident reporting, fair-use conflict handling, and audit history.

## Tech stack
- Python + Flask
- SQLite database
- HTML, CSS, Jinja templates, vanilla JavaScript

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended):
   - Windows PowerShell: `py -m venv .venv` then `.\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install packages: `pip install -r requirements.txt`
5. Start the app: `python app.py`
6. Open `http://127.0.0.1:5000`.

The SQLite database and sample data are initialized automatically on first run.

## Demo accounts
These are intentionally simple demo credentials for local judging only. Do not use them in production.

| Role | Email | Password |
|---|---|---|
| Resource owner | owner@sharespace.demo | owner123 |
| Student/user | student@sharespace.demo | student123 |
| Manager | manager@sharespace.demo | manager123 |
| Admin | admin@sharespace.demo | admin123 |

## End-to-end demo
1. Sign in as `owner@sharespace.demo`, add a resource from **List a resource**.
2. Sign out and sign in as `student@sharespace.demo`.
3. Open a resource, choose a start/end time, add a purpose, and request it.
4. Sign in as the owner and approve or reject the request from the booking panel.
5. Sign in as the student and record check-in condition, e.g. `No visible damage; accessories present`.
6. Record final condition on return.
7. Report an incident if needed.
8. Sign in as manager/admin and use **Admin & audit** to verify users, resolve incidents, and inspect action history.

## Implemented features
- Resource catalogue with search and category filters
- Owner-created listings with location, availability, requirements, rules, and deposit
- User/owner accounts and manager verification
- Booking requests, owner approval/rejection, waitlist on overlapping requests, and overlap protection
- Booking cancellation
- Check-in and return with initial/final condition notes
- Damage, delay, scheduling-conflict, and other incident reports
- Manager/admin verification and incident resolution
- Audit log of key actions
- Responsive dashboard and demo seed data

## Prototype limitations and safety notes
- Passwords are stored as plain text in this educational demo. Replace with password hashing (e.g. Werkzeug `generate_password_hash` / `check_password_hash`) before any real deployment.
- The app uses a development Flask server and a demo secret key. Set a strong `SECRET_KEY`, turn off debug mode, and use a production server before deployment.
- Date/time checks are basic; production use should add timezone-aware validation, stronger scheduling rules, email notifications, file/photo evidence uploads, and more complete authorization tests.
- Verification is a manager-controlled demo flag, not real identity verification. No real personal or confidential institutional data should be entered.
- This is a prototype, not a safety certification for restricted labs or dangerous equipment.
- AI is intentionally not used to make access or penalty decisions; this keeps the demo transparent and reviewable.
