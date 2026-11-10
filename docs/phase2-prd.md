# No-Shows, No Waste — Phase 2 PRD

## Executive summary
No-Shows, No Waste is a classroom MVP for hybrid workplace desks and meeting rooms. It addresses the mismatch between booked capacity and actual use: employees may be unable to find a space while previously booked desks or rooms remain unused. The MVP combines employee date/time availability and booking with a Facilities / Workplace Coordinator view for reviewing explainable risk flags and preparing respectful reminders.

The implemented AI capability is **Gemini-assisted reminder drafting** inside the coordinator workflow. The risk score is a deterministic heuristic—not GenAI, not a trained prediction model, and not an independent authority to cancel or release bookings.

## Target user and value
- **Primary user:** Facilities / Workplace Coordinator at a hybrid organisation.
- **Affected user:** Employee / Booker seeking or holding a desk or meeting-room booking.
- **Value proposition:** Help coordinators recover potentially unused capacity without replacing booking systems or removing employee control.

## Customer discovery
Supplied workbook: **25 survey submissions from 22 unique respondent IDs**.
- 22/25 (88%) had seen a booked desk/room go unused at least once.
- 18/25 (72%) had needed a space and found none available.
- 11/25 (44%) cited booking “just in case” as a main no-show reason.
- Top frustrations: difficulty finding a free space (8/25); booked-but-empty spaces (6/25).
- 10/25 reported doing nothing about no-shows; 10/25 said current approaches work only partly; 5/25 said they do not work.
- Auto-release sentiment: 15 answers only; 9 accepted if warned first, 5 if rebooking is easy, 1 strongly against.
- Reminder channel preference: 15 answers only; Teams/Slack 7, phone push 4, email 3, calendar alert 1.

**Opportunity hypothesis:** We believe Facilities Coordinators in hybrid offices struggle to recover booked desks and rooms when employees book “just in case” or forget to cancel. An explainable review workflow and respectful reminder could help return unused capacity, provided employees can confirm, cancel or request a change and are not penalised by an opaque score.

**Research limits:** This workbook is survey evidence, not interview transcripts. The 25 submissions are not 25 unique respondents. Question denominators vary. No completed 2–3-user walkthrough evidence was available at preparation time.

## MVP scope
- Booking information enters via synthetic/demo data or CSV import.
- Employee selects a date/time and sees desks and meeting rooms available for that exact interval.
- Booking engine prevents overlapping bookings for the same space; adjacent bookings are allowed.
- Coordinator reviews rule-based risk flags and contributing reasons.
- Gemini drafts reminder wording; deterministic template fallback is available.
- Notifications are simulated; no real email, Teams, Slack or calendar messages are sent.
- SQLite is prototype persistence, not a production master-data platform.

## Out of scope / future
- Separate employee and space master-data database and B2C-style management application.
- Live booking/calendar integrations and real external message delivery.
- GenAI-supported risk identification/explanations and policy-driven risk actions.
- Always-on scheduler, production authentication/access control, audit and retention infrastructure.
- Expansion into parking, rentals or flight booking without fresh domain discovery.

## Primary workflow
1. Coordinator loads demo bookings or imports CSV.
2. System calculates transparent rule-based risk signals.
3. Coordinator reviews flagged bookings and reasons; risk is advisory.
4. Coordinator requests a reminder draft.
5. Gemini receives only the booking facts needed and drafts a concise message.
6. Coordinator reviews/edits the message; send is simulated.
7. Employee response and booking state are represented in the prototype.

## AI capability
**Input:** employee name, space, booking date, start time, response/release deadline and coordinator/host identity.

**Processing:** Gemini is instructed to draft a friendly, neutral, concise message (under 70 words), use only supplied facts, offer KEEP / RESCHEDULE / CANCEL, state the deadline and avoid blame or risk-score references.

**Output:** editable reminder text for Coordinator review; deterministic template fallback if the key is absent or Gemini fails.

**Value:** less repetitive writing for coordinators and clearer next actions for employees.

**Discovery link:** survey evidence shows reminder use and a preference for Teams/Slack among the 15 who answered; warning-first/easy-rebooking conditions were accepted by 14/15 respondents to that question. This supports concise action-oriented messaging but does not prove AI wording is better than a template. User testing is needed.

## Risk score and guardrails
Current score uses historical no-show rate, lead time, recurring booking flag and check-in status; capped at 100. Bands: High ≥60; Medium 35–59; Low <35. It is advisory and must not independently cancel or release a booking.

## Check-in / release policy — separate from risk
- T−3 hours: check-in window opens; intended policy is one automatic reminder if employee has not already KEEP/Confirmed or CANCEL.
- KEEP retains/confirms; CANCEL releases immediately.
- RESCHEDULE goes to Coordinator approval; original booking remains protected while pending.
- No response by T−2: intended policy is auto-release, Coordinator notification and availability update for the exact space/date/time.
- Pending RESCHEDULE at T−2 remains unresolved policy and must not be silently assumed either a response or no response.
- The prototype has no always-on scheduler; processing depends on app execution/reruns. Exact wall-clock background execution is not guaranteed. Verify dispatch implementation before claiming full automation.

## User stories
| ID | Story | Acceptance |
|---|---|---|
| US1 | Coordinator loads bookings to review capacity | Demo and valid CSV rows load; invalid rows are reported |
| US2 | Coordinator sees risk band and reasons | Each active booking has readable contributing factors |
| US3 | Coordinator generates/edits a reminder | Message uses supplied facts and has clear action/deadline |
| US4 | Coordinator can continue without Gemini | Template fallback; AI failure does not alter booking state |
| US5 | Employee sees availability for selected date/time | Only spaces without overlapping active/confirmed bookings appear available |
| US6 | Employee books an available space | Availability is rechecked at save; conflicts rejected |

## Privacy and ethics
Beneficiaries include employees seeking workspace, coordinators and organisations. Potential harms include false-positive flags, unfair inconvenience for employees with legitimate schedule changes and erosion of trust. Use synthetic demo data; minimise fields; never use protected traits or infer intent; keep human oversight; protect API keys; define employee notice, access controls, retention, audit and deletion before production.

## Roadmap
- **MVP:** Streamlit prototype, demo/CSV, availability, heuristic flags, Gemini reminder draft, simulated notifications.
- **V2:** 2–3 user walkthroughs, UX iteration, tune rules with consented data, real booking/calendar integration, Teams/email, response capture, reliable scheduler, audit log.
- **Future:** separate employee/space database and app; GenAI-assisted risk identification/explanations; policy-configurable notifications/actions; multi-site analytics; explore other resource domains only after discovery.

## Success measures
North-star: confirmed unused capacity returned before another employee needs it. Supporting: reminder response rate, precision/false-positive rate, coordinator time saved, rebooking success and incorrect-release incidents.

## Deployment and validation
Repository: https://github.com/Sim-design8/no-shows-no-waste. PR #7 adds selected-date/time availability and scope clarification; it is open and not merged. Verify deployed branch and public Streamlit Cloud URL before submission. Uploaded package engine tests were reported as 14/14 passing; live UI walkthroughs and 2–3-user validation were not verified.
