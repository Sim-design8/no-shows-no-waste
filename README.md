# No-Shows, No Waste — Updated Phase 2 Prototype

## Positioning
A workplace space-recovery concept for facilities/workplace teams managing shared desks and meeting rooms. The core information gap is between **booking intent** and **actual use of the specific reserved space**.

## What this prototype demonstrates
- Booker and Coordinator views.
- Demo bookings and CSV booking import.
- Date/time availability checks and booking overlap prevention through the booking engine.
- Transparent, rule-based risk flags (advisory only).
- T−3 check-in reminder workflow with simulated notification; Gemini may draft wording, but does not decide policy.
- KEEP / CANCEL / RESCHEDULE response workflow supported by the booking engine.
- T−2 no-response release processing and coordinator notification, subject to the engine's current policy implementation.
- Optional manual CSV upload of usage evidence keyed by booking_id to illustrate the difference between booking intent and actual-use signals.

## Important execution limitation
The app processes due reminders/releases when Streamlit code executes or reruns. It does **not** include an always-on background scheduler. Do not describe this prototype as a continuously running production automation service. Notifications are simulated; no real email or Teams messages are sent.

## What is not implemented
- No live access-control/badge, Wi-Fi, sensor, IoT, Outlook, Google Calendar, Teams or Slack integrations.
- No verified occupancy detection. Uploaded usage evidence is manually supplied and is not independently validated.
- No production authentication, enterprise-grade authorization, persistent hosted database, or audit/compliance controls.
- No AI risk prediction or AI release decision. Risk is deterministic; Gemini is limited to optional reminder wording.

## Data
Use synthetic demo data or import the booking CSV template. The optional usage evidence CSV must contain:
- `booking_id`
- `usage_signal` (e.g. `Used`, `Not detected`, `Unknown`)

## Business rules
- Check-in window opens at T−3 hours.
- One reminder is generated at window opening for an Active booking not already KEEP/CANCEL.
- Window closes at T−2 hours.
- KEEP preserves; CANCEL releases immediately; RESCHEDULE is routed for coordinator approval and original booking remains protected while pending.
- No response by T−2 triggers release and coordinator notification.
- **Pending RESCHEDULE at T−2 remains a policy decision requiring confirmation; do not silently treat it as no response or auto-release it.**

## Competitive context
Skedda, Envoy and Eptura already offer check-in/reminder and automatic release capabilities. The opportunity is not to claim this basic workflow is unique; it is to test whether integration-light, explainable, policy-configurable capacity recovery solves an unmet gap for a defined customer segment.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```