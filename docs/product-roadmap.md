# Product roadmap — No-Shows, No Waste

| Horizon | Scope | Evidence / dependencies |
|---|---|---|
| MVP (current prototype) | Streamlit; demo/CSV booking input; date/time availability; overlap prevention; rule-based advisory flags; Gemini reminder drafting with template fallback; simulated notifications | Verify deployed branch, public URL and Gemini configuration; disclose no always-on scheduler or real message delivery |
| V2 — validate and integrate | 2–3 real user walkthroughs; improve UX; tune rules with consented outcome data; live booking/calendar integration; Teams/email delivery; employee response capture; reliable scheduled processing; audit log | User evidence, integration permissions, scheduler reliability, privacy/security review and false-positive baselines |
| Future — intelligent operations | GenAI-assisted identification/explanation of potentially risky bookings; policy-configurable employee/Coordinator notifications and actions; separate employee/space database and B2C-style application; multi-site analytics | Fresh discovery, fairness evaluation, policy/legal review, human override, production data and identity controls |
| Longer-term exploration | Parking, rental-space and potentially flight-booking resource workflows | Separate domain discovery and domain-specific rules, inventory systems, contracts, access control and regulatory review |

## Measures
- North-star: confirmed unused capacity returned to availability before another employee needs it.
- Leading: reminder response rate, coordinator review time, cancellation rate and rebooking rate.
- Guardrails: false-positive rate, employee complaints/appeals, incorrect release incidents and AI draft edit/rejection rate.
