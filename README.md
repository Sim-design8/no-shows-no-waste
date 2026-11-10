# No-Shows, No Waste — Streamlit MVP

A classroom prototype for reducing unused desk and meeting-room bookings in a hybrid workplace.

## MVP scope

### Employee / Booker
- Select a booking date and time.
- View desks and meeting rooms available for that exact date/time.
- Create a booking only when the selected space is available; overlapping bookings are prevented and back-to-back bookings are allowed.
- View existing bookings and respond with KEEP, CANCEL or RESCHEDULE.

### Booking data
- The MVP receives booking information from synthetic/demo data or CSV import.
- It does not include a production employee directory or full space-management system.

### Facilities / Workplace Coordinator
- Review flagged bookings and inspect the reasons behind each flag.
- The MVP risk score is a transparent, rule-based heuristic. It is advisory only and does not itself cancel or release a booking.
- Reminder and booking-response events are simulated; no real email, Teams, Slack or calendar messages are sent.

## Separate check-in and release workflow

Risk-based flagging and check-in-based release are separate mechanisms.

- At **T−3 hours**, the check-in window opens. If the employee has not already selected KEEP/Confirmed or CANCEL, the app automatically records one simulated reminder and sets the response deadline to **T−2 hours**.
- **KEEP** confirms and retains the booking. **CANCEL** releases it immediately.
- **RESCHEDULE** submits a request for Coordinator approval; the original booking remains protected while the request is pending. The handling of a request still pending at the T−2 deadline remains a product-policy decision and must not be silently assumed to count as either a response or no response.
- At **T−2 hours**, an unanswered booking is automatically marked Released, the Coordinator is notified, and availability for that exact desk/date/time is updated so another employee can book it.
- The Coordinator oversees bookings and reschedule decisions; they do not manually initiate automatic reminders or automatic releases.
- Reminder and release processing occurs when the Streamlit app executes/reruns. There is no always-on background scheduler, so an idle app cannot guarantee exact wall-clock execution. Production requires a durable scheduled worker.

## Future scope (not implemented in this MVP)

- A separate employee-facing B2C-style application and a dedicated database to manage employees, spaces, and related master data.
- GenAI-supported identification of potentially risky bookings and richer explanations for the Coordinator. This is future functionality; current risk scoring is rule-based.
- Future policy-driven actions based on risk, including notifying employees and the Coordinator. Risk scores do not autonomously trigger cancellation or release in the current MVP.
- Expansion to other resource domains (for example, parking, flights or rental spaces) requires separate discovery, policy and integration work.

## AI capability in the current prototype

Gemini is optional and is used only to draft concise reminder wording from supplied booking facts. A deterministic template is used when Gemini is unavailable. Gemini does not calculate the risk score, decide who loses access, approve reschedules, or determine whether a booking is released.

## Run on Windows

```bat
py -m pip install -r requirements.txt
py test_booking_engine.py
py -m streamlit run app.py
```

The app opens at `http://localhost:8501`. Keep the terminal open; stop with Ctrl+C.

## Prototype boundaries and privacy

- The Booker/Coordinator view switcher is a demonstration convenience, not authentication or access control.
- Seeded people and bookings are synthetic. Avoid uploading real employee personal or sensitive data.
- CSV substitutes for calendar integrations.
- Notifications are simulated; no real messages are sent.
- SQLite is suitable for this local classroom prototype. Streamlit Cloud local storage may be ephemeral and is not production persistence.
- Do not commit API keys to GitHub.

## CSV format

Required columns: `booking_id, space, booking_date, start_time, end_time, coordinator_name, coordinator_email, booker_name, booker_email, team`.
