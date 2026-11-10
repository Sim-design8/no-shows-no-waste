# No-Shows, No Waste — redesigned Streamlit MVP

A refreshed, two-view Streamlit interface inspired by the supplied coordinator and workspace-booker design references.

## Views
- **Booker (Employee):** create a desk/room booking, see personal bookings, and respond with KEEP, RESCHEDULE or CANCEL.
- **Coordinator (Facilities):** review daily bookings, inspect explainable rule-based risk signals, draft reminder text with optional Gemini, simulate sending, and approve/reject reschedule requests.

## Run on Windows
Open Command Prompt in this folder and run:

```bat
py -m pip install -r requirements.txt
py test_booking_engine.py
py -m streamlit run app.py
```

The app opens at `http://localhost:8501`. Keep the terminal open; stop with Ctrl+C.

## Prototype boundaries
- The two-view switcher is a demonstration convenience, not real authentication or access control.
- Seeded people and bookings are synthetic.
- CSV substitutes for calendar integrations.
- Email delivery is simulated; no real messages are sent.
- Risk score is a transparent heuristic, not an AI prediction.
- Gemini is optional and only drafts reminder wording; a template is used if unavailable.
- SQLite is suitable for this local classroom prototype. Streamlit Cloud's local filesystem may be ephemeral and is not production persistence.

## CSV format
Required columns: `booking_id, space, booking_date, start_time, end_time, coordinator_name, coordinator_email, booker_name, booker_email, team`.

## Important
This update refreshes the visual presentation while retaining the booking-engine workflow. Back up any existing `no_shows_bookings.db` before replacing local project files. Do not commit API keys to GitHub.
