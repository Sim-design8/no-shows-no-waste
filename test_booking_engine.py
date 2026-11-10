"""Run: python test_booking_engine.py"""
import os
import tempfile
import threading
from datetime import datetime

import pandas as pd

import booking_engine as be

D = "2026-11-12"


def fresh():
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    be.init_db(path)
    return path


def bk(i, space="Desk D-12", start="10:00", end="11:00", email=None):
    return {"booking_id": i, "space": space, "booking_date": D, "start_time": start, "end_time": end,
            "coordinator_name": "Facilities Desk", "coordinator_email": "fd@example.com",
            "booker_name": i, "booker_email": email or f"{i}@example.com", "team": "Eng"}


def at(h, m=0):
    return datetime(2026, 11, 12, h, m)


def test_overlap_and_adjacent():
    db = fresh()
    assert be.create_booking(bk("A"), db)[0]
    assert not be.create_booking(bk("B"), db)[0]                                   # same slot
    assert not be.create_booking(bk("C", start="10:30", end="11:30"), db)[0]       # overlap
    assert not be.create_booking(bk("C", start="09:30", end="10:30"), db)[0]       # overlap before
    assert be.create_booking(bk("D", start="11:00", end="12:00"), db)[0]           # adjacent after
    assert be.create_booking(bk("E", start="09:00", end="10:00"), db)[0]           # adjacent before
    assert be.create_booking(bk("F", space="Desk D-13"), db)[0]                    # other space


def test_invalid_input():
    db = fresh()
    assert not be.create_booking(bk("A", start="11:00", end="10:00"), db)[0]
    assert not be.create_booking(bk("A", start="25:00", end="26:00"), db)[0]
    assert be.create_booking(bk("A"), db)[0]
    assert not be.create_booking(bk("A", space="Desk D-1"), db)[0]                 # duplicate ID


def test_concurrent_double_booking():
    db = fresh()
    results = []

    def attempt(n):
        results.append(be.create_booking(bk(f"T{n}"), db)[0])

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 1, results
    assert len(be.list_bookings(db, D)) == 1


def test_csv_import_report():
    db = fresh()
    df = pd.DataFrame([bk("A"), bk("B"), bk("C", space="Desk D-1"),
                       {**bk("D", space="Desk D-2"), "booker_email": ""}])
    rep = be.import_bookings(df, db)
    assert rep["imported"] == ["A", "C"]
    assert {r[0] for r in rep["rejected"]} == {"B", "D"}
    assert "Missing" in be.import_bookings(df.drop(columns=["team"]), db)["rejected"][0][1]


def test_reminder_window_rules():
    db = fresh()
    be.create_booking(bk("A", start="12:00", end="13:00"), db)       # window 09:00-10:00
    assert not be.send_reminder("A", "s", "b", at(8, 59), db)[0]     # too early
    assert be.send_reminder("A", "s", "b", at(9, 30), db)[0]
    assert not be.send_reminder("A", "s", "b", at(10, 0), db)[0]     # deadline reached


def test_keep_cancel_and_auto_release():
    db = fresh()
    for i, sp in (("K", "Desk D-1"), ("C", "Desk D-2"), ("N", "Desk D-3"), ("U", "Desk D-4")):
        be.create_booking(bk(i, space=sp, start="12:00", end="13:00"), db)
        if i != "U":
            be.send_reminder(i, "s", "b", at(9, 10), db)
    assert be.respond("K", "KEEP", at(9, 20), db)[0]
    assert be.respond("C", "CANCEL", at(9, 21), db)[0]
    assert be.create_booking(bk("NEW", space="Desk D-2", start="12:00", end="13:00"), db)[0]  # slot reusable
    assert be.process_deadlines(at(9, 59), db) == []
    assert be.process_deadlines(at(10, 0), db) == ["N"]              # only reminded + unconfirmed
    assert be.get_booking("K", db)["status"] == "Confirmed"
    assert be.get_booking("U", db)["status"] == "Active"             # never warned -> never auto-released
    assert be.create_booking(bk("N2", space="Desk D-3", start="12:00", end="13:00"), db)[0]
    assert be.process_deadlines(at(10, 5), db) == []                 # idempotent


def test_reschedule_available_slot_still_requires_approval():
    db = fresh()
    be.create_booking(bk("A"), db)
    ok, msg = be.respond("A", "RESCHEDULE", at(9), db, (D, "14:00", "15:00"))
    assert ok and "coordinator approval" in msg
    # Requesting a free slot must not silently alter or confirm the original booking.
    original = be.get_booking("A", db)
    assert (original["booking_date"], original["start_time"], original["end_time"], original["status"]) == (D, "10:00", "11:00", "Active")
    requests = be.pending_requests(db)
    assert len(requests) == 1
    assert (requests[0]["new_date"], requests[0]["new_start"], requests[0]["new_end"]) == (D, "14:00", "15:00")
    # Only explicit coordinator approval may move the booking.
    approved, approval_msg = be.approve_reschedule(requests[0]["request_id"], at(9, 5), db)
    assert approved and "updated" in approval_msg
    updated = be.get_booking("A", db)
    assert (updated["start_time"], updated["status"]) == ("14:00", "Confirmed")
    assert be.is_available("Desk D-12", D, "10:00", "11:00", db)


def test_reschedule_unavailable_approval_flow():
    db = fresh()
    be.create_booking(bk("A"), db)
    be.create_booking(bk("B", start="14:00", end="15:00"), db)
    ok, msg = be.request_reschedule("A", D, "14:00", "15:00", at(9), db)
    assert ok and "coordinator" in msg
    assert be.get_booking("A", db)["start_time"] == "10:00"          # original protected
    q = be.pending_requests(db)[0]
    # someone else's booking is cancelled -> approval succeeds after re-check
    be.respond("B", "CANCEL", at(9, 5), db)
    ok, _ = be.approve_reschedule(q["request_id"], at(9, 10), db)
    assert ok and be.get_booking("A", db)["start_time"] == "14:00"


def test_approval_rechecks_availability():
    db = fresh()
    be.create_booking(bk("A"), db)
    be.create_booking(bk("B", start="14:00", end="15:00"), db)
    be.request_reschedule("A", D, "14:00", "15:00", at(9), db)
    q = be.pending_requests(db)[0]
    be.respond("B", "CANCEL", at(9, 1), db)
    assert be.create_booking(bk("C", start="14:00", end="15:00"), db)[0]   # someone else grabs it meanwhile
    ok, msg = be.approve_reschedule(q["request_id"], at(9, 10), db)
    assert not ok and "taken" in msg
    assert be.get_booking("A", db)["start_time"] == "10:00"                # original retained
    assert be.get_booking("C", db)["start_time"] == "14:00"                # newer booking not overwritten


def test_reject_keeps_original_and_applies_no_response_policy():
    db = fresh()
    be.create_booking(bk("A", start="12:00", end="13:00"), db)
    be.create_booking(bk("B", start="14:00", end="15:00"), db)
    be.request_reschedule("A", D, "14:00", "15:00", at(9, 0), db)
    q = be.pending_requests(db)[0]
    ok, _ = be.reject_reschedule(q["request_id"], at(9, 40), db)
    assert ok and be.get_booking("A", db)["status"] == "Active"            # not released by the rejection itself
    assert be.process_deadlines(at(9, 59), db) == []
    assert be.process_deadlines(at(10, 15), db) == ["A"]                   # no reply by respond_by -> released
    # alternatively KEEP
    be.create_booking(bk("Z", space="Desk D-12", start="12:00", end="13:00"), db)
    be.request_reschedule("Z", D, "14:00", "15:00", at(9, 0), db)
    be.reject_reschedule(be.pending_requests(db)[0]["request_id"], at(9, 40), db)
    assert be.respond("Z", "KEEP", at(9, 45), db)[0] and be.get_booking("Z", db)["status"] == "Confirmed"


def test_risk_review_queue_only_includes_t2_no_response_releases():
    db = fresh()
    for booking_id, space in (("EARLY", "Desk D-31"), ("KEEP", "Desk D-32"),
                              ("CANCEL", "Desk D-33"), ("NO_REPLY", "Desk D-34")):
        be.create_booking(bk(booking_id, space=space, start="12:00", end="13:00"), db)

    # Confirmed before the check-in window: no reminder and no risk review.
    assert be.respond("EARLY", "KEEP", at(8, 0), db)[0]
    # KEEP during the T−3 to T−2 window: retained and excluded.
    assert be.send_reminder("KEEP", "s", "b", at(9, 10), db)[0]
    assert be.respond("KEEP", "KEEP", at(9, 30), db)[0]
    # CANCEL during the window: released by the employee, not risk-review eligible.
    assert be.send_reminder("CANCEL", "s", "b", at(9, 10), db)[0]
    assert be.respond("CANCEL", "CANCEL", at(9, 30), db)[0]
    # No response by T−2: automatically released and queued for coordinator review.
    assert be.send_reminder("NO_REPLY", "s", "b", at(9, 10), db)[0]
    assert be.process_deadlines(at(10, 0), db) == ["NO_REPLY"]

    assert be.get_booking("EARLY", db)["status"] == "Confirmed"
    assert be.get_booking("KEEP", db)["status"] == "Confirmed"
    assert be.get_booking("CANCEL", db)["status"] == "Cancelled"
    assert be.get_booking("NO_REPLY", db)["status"] == "Released"
    assert [b["booking_id"] for b in be.risk_review_queue(db)] == ["NO_REPLY"]


def test_alternatives():
    db = fresh()
    be.create_booking(bk("A", space="Desk D-12"), db)
    be.create_booking(bk("B", space="Desk D-13"), db)
    be.create_booking(bk("C", space="Desk D-14", start="12:00", end="13:00"), db)
    alts = be.suggest_alternatives("Desk D-12", D, "10:00", "11:00", db)
    assert any(a["space"] == "Desk D-14" and a["start"] == "10:00" for a in alts)
    assert all(a["space"] != "Desk D-13" or a["start"] != "10:00" for a in alts)


def test_repeated_reschedule_submission_is_idempotent():
    db = fresh()
    be.create_booking(bk("A"), db)
    first = be.request_reschedule("A", D, "14:00", "15:00", at(9), db)
    second = be.request_reschedule("A", D, "14:00", "15:00", at(9, 1), db)
    assert first[0] and second[0]
    assert "already pending" in second[1]
    assert len(be.pending_requests(db)) == 1
    assert be.get_booking("A", db)["start_time"] == "10:00"


def test_concurrent_reschedule_submissions_create_one_request():
    db = fresh()
    be.create_booking(bk("A"), db)
    results = []

    def submit(n):
        results.append(be.request_reschedule("A", D, "14:00", "15:00", at(9, n), db))

    threads = [threading.Thread(target=submit, args=(n,)) for n in range(10)]
    [thread.start() for thread in threads]
    [thread.join() for thread in threads]
    assert all(ok for ok, _ in results), results
    assert len(be.pending_requests(db)) == 1


def test_new_request_allowed_after_previous_request_is_handled():
    db = fresh()
    be.create_booking(bk("A"), db)
    be.request_reschedule("A", D, "14:00", "15:00", at(9), db)
    q = be.pending_requests(db)[0]
    assert be.reject_reschedule(q["request_id"], at(9, 10), db)[0]
    ok, msg = be.request_reschedule("A", D, "16:00", "17:00", at(9, 20), db)
    assert ok and "coordinator approval" in msg
    assert len(be.pending_requests(db)) == 1


def test_keep_closes_pending_reschedule_request():
    db = fresh()
    be.create_booking(bk("A"), db)
    ok, msg = be.request_reschedule("A", D, "14:00", "15:00", at(9), db)
    assert ok
    request_id = be.pending_requests(db)[0]["request_id"]

    kept, keep_msg = be.respond("A", "KEEP", at(9, 5), db)
    assert kept and "pending reschedule requests closed" in keep_msg.lower()
    assert be.get_booking("A", db)["status"] == "Confirmed"
    assert be.pending_requests(db) == []

    # A stale coordinator action must not move a booking after KEEP.
    approved, approve_msg = be.approve_reschedule(request_id, at(9, 10), db)
    assert not approved and "already handled" in approve_msg
    booking = be.get_booking("A", db)
    assert booking["start_time"] == "10:00"
    assert booking["status"] == "Confirmed"


def test_csv_import_preserves_confirmed_status_and_parses_boolean_values():
    db = fresh()
    confirmed = {**bk("CONF", space="Desk D-20"), "status": "Confirmed", "recurring": "False",
                 "past_bookings": "3", "past_no_shows": "1", "lead_days": "2"}
    active = {**bk("ACT", space="Desk D-21"), "status": "Active", "recurring": "true"}
    report = be.import_bookings(pd.DataFrame([confirmed, active]), db)
    assert report["imported"] == ["CONF", "ACT"]
    assert be.get_booking("CONF", db)["status"] == "Confirmed"
    assert be.get_booking("CONF", db)["recurring"] == 0
    assert be.get_booking("ACT", db)["recurring"] == 1
    assert be.get_booking("CONF", db)["past_bookings"] == 3


def test_csv_import_rejects_invalid_numeric_and_boolean_rows_without_aborting():
    db = fresh()
    bad_number = {**bk("BADNUM", space="Desk D-22"), "past_no_shows": "many"}
    bad_bool = {**bk("BADBOOL", space="Desk D-23"), "recurring": "sometimes"}
    good = bk("GOOD", space="Desk D-24")
    report = be.import_bookings(pd.DataFrame([bad_number, bad_bool, good]), db)
    assert report["imported"] == ["GOOD"]
    assert {r[0] for r in report["rejected"]} == {"BADNUM", "BADBOOL"}


def test_send_reminder_is_idempotent_and_rejects_confirmed_booking():
    db = fresh()
    be.create_booking({**bk("A", start="12:00", end="13:00"), "status": "Active"}, db)
    first = be.send_reminder("A", "subject", "body", at(9, 10), db)
    second = be.send_reminder("A", "subject", "body", at(9, 11), db)
    assert first[0]
    assert not second[0] and "already been sent" in second[1]
    assert len([n for n in be.notifications(db) if n["kind"] == "reminder"]) == 1
    be.create_booking({**bk("C", space="Desk D-25", start="12:00", end="13:00"), "status": "Confirmed"}, db)
    assert not be.send_reminder("C", "subject", "body", at(9, 10), db)[0]


def test_rejecting_reschedule_does_not_downgrade_confirmed_booking():
    db = fresh()
    be.create_booking({**bk("A"), "status": "Confirmed"}, db)
    assert be.request_reschedule("A", D, "14:00", "15:00", at(9), db)[0]
    request = be.pending_requests(db)[0]
    assert be.reject_reschedule(request["request_id"], at(9, 10), db)[0]
    booking = be.get_booking("A", db)
    assert booking["status"] == "Confirmed"
    assert booking["reminder_sent_at"] is None
    assert booking["respond_by"] is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\nAll {len(tests)} tests passed")
