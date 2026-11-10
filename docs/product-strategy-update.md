# Product Strategy Update — No-Shows, No Waste
Updated: 11 November 2026

## Problem framing
A booking records intent; it does not prove use of the specific reserved desk or meeting room. Keep three signals distinct:
1. Booking status — what was reserved, by whom, and for what interval.
2. Building attendance — whether the employee entered the building; this does not prove use of the reserved resource.
3. Resource-use evidence — whether the specific desk/room was used during the reserved interval.

Signals may sit in separate booking, calendar, access-control, Wi-Fi, sensor or manual systems. The current prototype does not integrate those systems.

## Target hypothesis
Primary MVP user: Facilities / Workplace Coordinator. Secondary user: employee/booker.
Initial ICP hypothesis: Indian hybrid enterprises with shared desks/rooms, recurring booking volume and fragmented booking/usage signals. Coworking operators are an adjacent reference segment for discovery, not yet the primary target.

## Customer evidence (supplied survey)
- 25 submissions; 22 unique respondent IDs (duplicates present).
- 22/25 (88%) had seen booked space go unused.
- 18/25 (72%) had needed a space but found none available.
- Top frustrations: finding free space (8/25), booked-but-empty space (6/25).
- No-show reasons: booked just in case (11/25), forgot to cancel (7/25).
These results indicate perceived pain in this sample. They do not prove system fragmentation, unmet demand versus incumbent products, willingness to pay or market size.

## Market context
Mordor Intelligence estimates the global space-management and desk-booking software category at USD 3.86B in 2026, forecasting USD 7.04B by 2031 (12.77% CAGR). This is broad category context, not our TAM/SAM. India software SAM requires bottom-up sizing from validated target accounts, sites and annual contract value. Do not substitute the broader facilities-management services market.

## Competition
- Skedda: check-in reminders, confirmation and configurable automatic release.
- Envoy: Space Saver releases desks when users do not check in; workplace analytics.
- Eptura Engage: automated check-in/release, occupancy updates and sensor integrations.
- Robin and OfficeSpace: presence, booking and utilization analytics.
Conclusion: reminders, check-in and auto-release are not unique differentiators.

## Differentiation hypotheses to validate
- CSV-first/integration-light deployment alongside an existing booking platform.
- Configurable policy controls and an explainable coordinator exception queue.
- Measure recovered capacity (released hours and rebooking rate).
These are hypotheses, not validated advantages.

## MVP today
- Demo/CSV booking intake; date/time availability; overlap prevention.
- Transparent rule-based risk score (advisory only).
- Simulated T−3 reminder, employee response and T−2 release workflow.
- Optional manually uploaded usage-evidence CSV keyed by booking_id.
- Optional Gemini reminder wording only; AI does not calculate risk, approve reschedules or release bookings.
- App processes due events only when Streamlit executes/reruns; no persistent background scheduler.
- No live badge/access, Wi-Fi, sensor, calendar, Teams or Slack integrations.

## Confirmed workflow
- T−3: open one-hour check-in window; if not already KEEP/CANCEL, generate one reminder.
- KEEP preserves; CANCEL releases immediately.
- RESCHEDULE submits to coordinator; original booking remains protected pending decision.
- T−2: no response releases, notifies coordinator and refreshes availability for the exact resource/date/time.
- Pending RESCHEDULE at T−2 is protected from auto-release until coordinator decision. A maximum decision SLA/escalation remains an open product-policy choice.

## Roadmap
1. Academic MVP: demo/CSV, availability, rule-based flags, simulated confirmation/release, manual usage-evidence overlay.
2. Validate: interview 3 workplace coordinators, 2 employees and 1 coworking operator; map existing platform capabilities and system boundaries.
3. Pilot: one booking source + one approved usage signal; persistent scheduler, audit trail and policy controls.
4. Scale: multi-site capacity metrics and configurable workflows. Parking, rentals and flights require separate discovery and rules.

## Validation gaps
No verified user walkthroughs, deployment validation, willingness-to-pay evidence, India software SAM or live occupancy integration is claimed in this repository update.
