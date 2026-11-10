# Product Requirements — No-Shows, No Waste (Updated)
Updated: 11 November 2026 | DPM2026-Gr15

## 1. Product intent
Help workplace teams manage shared desk and meeting-room capacity by making booking status, employee confirmation and available usage evidence easier to review. A booking is intent, not proof that the specific reserved resource was used.

## 2. Users
- Primary: Facilities / Workplace Coordinator.
- Secondary: Employee / Booker.
- Proposed buyer to validate: Head of Workplace, Facilities, Corporate Real Estate or Workplace Operations.

## 3. Problem statement
A coordinator may know that a desk/room was booked without knowing whether the specific resource was used. Building entry is not sufficient proof: an employee may enter and use another space, leave early or change plans. Booking, calendar, access-control, Wi-Fi and sensor signals may be separate. This system fragmentation is a discovery hypothesis, not proven by the current survey.

## 4. MVP scope
- Synthetic/demo and CSV booking intake.
- Date/time-specific availability and overlap prevention.
- Rule-based, explainable risk score; advisory only.
- T−3 one-time simulated reminder if booking is not already KEEP/CANCEL.
- KEEP, CANCEL and RESCHEDULE employee actions.
- Coordinator approval/rejection of reschedule requests.
- T−2 no-response release, coordinator notification and availability refresh.
- Optional manual usage-evidence CSV view keyed by booking_id.
- Optional Gemini reminder wording only, with template fallback.

## 5. Out of scope
- Live badge/access, Wi-Fi, sensor, IoT, calendar, Teams or Slack integrations.
- Actual occupancy verification.
- AI risk prediction or autonomous release.
- Production authentication/authorization, durable hosted database or always-on scheduler.
- Expansion to flights, parking or rentals in the MVP.

## 6. Functional requirements
FR-01: Employee selects date and start/end time before viewing spaces.
FR-02: Only spaces with no overlapping active booking are shown.
FR-03: Overlap condition is new_start < existing_end AND new_end > existing_start; adjacent bookings are allowed.
FR-04: Coordinator sees bookings, status and transparent risk reasons.
FR-05: Risk score cannot itself cancel or release.
FR-06: At T−3, system checks status and generates one reminder only if not already KEEP/CANCEL.
FR-07: KEEP retains; CANCEL releases immediately.
FR-08: RESCHEDULE creates a pending coordinator request; original booking remains protected.
FR-09: At T−2, no response releases the booking, notifies coordinator and refreshes availability for the exact resource/date/time.
FR-10: A pending RESCHEDULE is protected from no-response auto-release until coordinator decision.
FR-11: Optional usage-evidence CSV requires booking_id and usage_signal; evidence is labelled manual and unverified.
FR-12: Gemini may draft reminder wording from supplied facts only; template fallback is required.

## 7. AI specification
Input: supplied employee name, resource, date, start time and response deadline.
Processing: Gemini writes friendly, neutral reminder text under 70 words using only supplied facts.
Output: reminder wording in simulated notification flow.
Guardrails: AI does not calculate risk, infer attendance, approve reschedules or release bookings. No sensitive inference or blame.

## 8. Non-functional and trust requirements
- Use synthetic data for demos; avoid sensitive employee data.
- Clearly distinguish booking, building attendance and resource-use evidence.
- Do not present manual usage evidence as verified.
- Explain that Streamlit execution/reruns process due events; no persistent background scheduler is included.
- Notifications are simulated; no real messages are sent.
- Production requires secure access controls, audit trail, durable storage, scheduler, privacy review and approved integrations.

## 9. Success measures
- Booking import success and rejection rates.
- Availability correctness and overlap-prevention rate.
- Reminder idempotency and response rate.
- False release/dispute rate.
- Released hours and rebooking rate of released spaces.
- Coordinator time spent identifying unused bookings.
- Coverage and confidence of booking-to-usage evidence.

## 10. Open decisions and validation
- Pending RESCHEDULE has no maximum decision SLA yet; define escalation/timeout policy with coordinators.
- Validate whether target customers have an unmet gap after existing Skedda/Envoy/Eptura/OfficeSpace/Robin capabilities are configured.
- Validate buyer, budget, integration feasibility and willingness to pay.
- India software SAM is not established; use bottom-up account/site/ACV sizing.
- Conduct 3 coordinator, 2 employee and 1 coworking-operator discovery sessions; do not represent these as completed until evidence exists.
