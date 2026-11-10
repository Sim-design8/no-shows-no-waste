# No-Shows, No Waste — final local MVP package

A college-project prototype with two experiences in one Streamlit app:

- **Booker (Employee):** request a space, see personal bookings, and respond to reminders with KEEP, RESCHEDULE or CANCEL.
- **Coordinator (Facilities):** review bookings, inspect rule-based risk signals, draft/send simulated reminders, and approve or reject reschedule requests.

The coordinator is the booking host. The booker's email identifies the requester.

## Files

- `app.py` — Streamlit interface with Booker and Coordinator views.
- `booking_engine.py` — SQLite booking, availability, reminder, response and reschedule workflow.
- `test_booking_engine.py` — 11 automated tests, including concurrent booking protection and coordinator approval checks.
- `requirements.txt` — Python packages.
- `sample_bookings.csv` — sample CSV for importing synthetic calendar bookings.

The database file `no_shows_bookings.db` is created automatically the first time the app starts. **Do not create it manually.** If you already have a database from an earlier version, back it up before replacing project files. Existing database records are not automatically migrated or reset.

## Windows setup (beginner-friendly)

Open Command Prompt in this folder. Then run these commands one at a time:

```bat
py -m pip install -r requirements.txt
py test_booking_engine.py
py -m streamlit run app.py
```

The app should open at `http://localhost:8501`. Keep the Command Prompt window open while using it. Stop the app with `Ctrl+C` in that window.

## How rescheduling works

1. The booker submits a proposed date/time.
2. The system checks availability for information, but does **not** accept the request automatically.
3. The request appears in the Coordinator's **Reschedule approvals** tab.
4. On approval, availability is checked again inside the database transaction before the booking is changed.
5. If rejected, the original booking remains active and the booker is asked to KEEP or CANCEL.

## CSV import

Use `sample_bookings.csv` as a template. Required columns:

`booking_id, space, booking_date, start_time, end_time, coordinator_name, coordinator_email, booker_name, booker_email, team`

Optional columns include `status`, `past_bookings`, `past_no_shows`, `lead_days`, and `recurring`. Dates use `YYYY-MM-DD`; times use `HH:MM`.

## Prototype boundaries

- CSV is used instead of direct Outlook/Google Calendar integration.
- Email notifications are simulated; no real emails are sent.
- All seeded/sample people and bookings are synthetic.
- Risk scoring is a transparent rule-based heuristic. Gemini is optional and only drafts reminder wording.
- SQLite is suitable for this local classroom prototype, not a production multi-instance deployment.
- There is no real authentication or role-based access control; the view switcher is for demonstration.

## Gemini (optional)

The app works without a Gemini API key and uses a template reminder. To enable AI-drafted reminder text, enter a Gemini API key in the Coordinator sidebar. Do not commit API keys to GitHub.

## Before submission

Update the AI-use disclosure in your project submission to accurately name the tools actually used by your group. Do not claim real calendar integration, real email delivery, or real user testing unless you have completed those activities.
