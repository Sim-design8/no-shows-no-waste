# Product scope clarification — No-Shows, No Waste

This note is the scope authority for the MVP/future distinction. It supplements the existing PRD and workflow documentation.

## MVP: employee availability and booking
1. Employee selects a date and time.
2. The product shows desks and meeting rooms available for that exact date/time.
3. Employee can create a booking only for a space that is available for the selected date/time.
4. Overlapping bookings for the same space are blocked; adjacent bookings are permitted.

## MVP: booking data and administration boundary
- Booking information enters the MVP through synthetic/demo data or CSV import.
- A separate database and application to manage spaces and employees through a B2C-style experience are future build scope, not part of this MVP.

## MVP: Coordinator risk review
- Coordinator reviews flagged bookings and sees the reasons/contributing factors.
- Current risk score is rule-based and advisory.
- Risk score does not independently cancel, release, or deny a booking.
- The current rule-based risk score must not be described as GenAI.

## Future capabilities
- GenAI-supported identification of potentially risky bookings and GenAI-generated explanations for Coordinator review.
- Future policy-driven employee and Coordinator notifications and risk-based actions. These are not implemented in the MVP; a risk flag alone must not cause release.
- Separate employee/space master-data application and database.

## Keep the two workflows distinct

### Risk review
Rule-based risk score → Coordinator reviews flag and reasons → no automatic booking action from risk score in MVP.

### Check-in and no-response release
- T−3h: check-in window opens; app checks employee status and automatically sends one simulated reminder only if there is no prior KEEP/Confirmed or CANCEL.
- KEEP: confirm and retain.
- CANCEL: release immediately.
- RESCHEDULE: route to Coordinator approval; retain the original booking while pending. **Policy for a request still pending at T−2h is unresolved and must not be invented in requirements or code.**
- No response by T−2h: automatically release, notify Coordinator, and make the exact desk/date/time available again.

The check-in release rule is separate from risk scoring. A booking is not released because it has a high risk score.

## Acceptance criteria to carry into implementation
- Given a selected date/time, the employee can see only spaces with no overlapping active/confirmed booking in that interval.
- Given a selected space/date/time that overlaps an active/confirmed booking, booking creation is rejected.
- Given a flagged booking, the Coordinator can inspect its contributing reasons.
- Given any risk band, no booking is automatically cancelled/released solely because of that risk band.
- Given an unanswered booking at T−2h, the check-in workflow releases it, notifies the Coordinator, and updates availability for the exact slot.
- A pending RESCHEDULE at T−2h must follow an explicitly approved product policy; until that policy is confirmed, do not claim it is safely handled by the implementation.
