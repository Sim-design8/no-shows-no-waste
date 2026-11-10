"""
Booking engine for No-Shows, No Waste (college MVP, SQLite prototype).

Rules implemented (see PRD):
- A booking is created or rescheduled only if no ACTIVE/CONFIRMED booking overlaps the same space and time.
  Overlap: new_start < existing_end AND new_end > existing_start (back-to-back bookings are fine).
- The availability check and the save happen in ONE transaction (BEGIN IMMEDIATE), so two simultaneous
  requests cannot both take the same slot.
- Check-in window: opens 3 h before start, closes (deadline) 2 h before start.
- KEEP confirms; CANCEL releases immediately; RESCHEDULE always creates a coordinator approval request.
  The original booking remains active until approval; availability is re-checked inside the approval transaction.
  Repeated submissions reuse the existing pending request; only one pending request per booking is allowed.
- A booking that was sent a reminder and is still unconfirmed at its response deadline is auto-released.

Limit: SQLite transactions protect one database file. A multi-server production system would use
PostgreSQL with an exclusion constraint.
"""

import os
import re
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "no_shows_bookings.db"
DAY_START, DAY_END = "08:00", "20:00"
LIVE = ("Active", "Confirmed")
OPENS_HOURS, DEADLINE_HOURS = 3, 2
REJECT_GRACE_MIN = 30
FMT = "%Y-%m-%d %H:%M"

REQUIRED = ["booking_id", "space", "booking_date", "start_time", "end_time",
            "coordinator_name", "coordinator_email", "booker_name", "booker_email", "team"]
OPTIONAL = {"status": "Active", "past_bookings": 0, "past_no_shows": 0, "lead_days": 0, "recurring": 0}

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings(
  booking_id TEXT PRIMARY KEY, space TEXT NOT NULL, booking_date TEXT NOT NULL,
  start_time TEXT NOT NULL, end_time TEXT NOT NULL,
  coordinator_name TEXT, coordinator_email TEXT, booker_name TEXT, booker_email TEXT, team TEXT,
  status TEXT NOT NULL DEFAULT 'Active',
  past_bookings INTEGER DEFAULT 0, past_no_shows INTEGER DEFAULT 0,
  lead_days INTEGER DEFAULT 0, recurring INTEGER DEFAULT 0,
  reminder_sent_at TEXT, respond_by TEXT, updated_at TEXT,
  risk_review_eligible INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS spaces(space TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS reschedule_requests(
  request_id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id TEXT NOT NULL,
  new_date TEXT, new_start TEXT, new_end TEXT,
  status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT);
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, booking_id TEXT,
  kind TEXT, to_email TEXT, subject TEXT, body TEXT);
"""


# ----------------------------------------------------------------------------- helpers
def connect(db=DB_PATH):
    conn = sqlite3.connect(db, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db=DB_PATH):
    conn = connect(db)
    try:
        conn.executescript(SCHEMA)
        # Existing SQLite databases need this additive migration; new databases
        # already receive the column from SCHEMA above.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(bookings)")}
        if "risk_review_eligible" not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN risk_review_eligible INTEGER NOT NULL DEFAULT 0")
        # Migration safety: older app versions could have created several pending
        # requests for one booking. Keep the newest and mark older ones superseded.
        conn.execute(
            "UPDATE reschedule_requests SET status='Superseded' "
            "WHERE status='Pending' AND request_id NOT IN "
            "(SELECT MAX(request_id) FROM reschedule_requests "
            "WHERE status='Pending' GROUP BY booking_id)"
        )
        # Database-level protection against rapid/replayed/concurrent submissions.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_one_pending_reschedule_per_booking "
            "ON reschedule_requests(booking_id) WHERE status='Pending'"
        )
    finally:
        conn.close()


def reset_db(db=DB_PATH):
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(db + suffix)
        except FileNotFoundError:
            pass
    init_db(db)


def now_str(now):
    return now.strftime(FMT)


def dt(date_s, time_s):
    return datetime.strptime(f"{date_s} {time_s}", FMT)


def norm_time(t):
    t = str(t).strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(:\d{2})?", t)
    if not m:
        raise ValueError(f"Invalid time '{t}' (use HH:MM)")
    h, mi = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        raise ValueError(f"Invalid time '{t}'")
    return f"{h:02d}:{mi:02d}"


def norm_date(d):
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d")
    try:
        return datetime.strptime(str(d).strip()[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date '{d}' (use YYYY-MM-DD)")


def validate_slot(date_s, start, end):
    """Returns normalised (date, start, end) or raises ValueError."""
    d, s, e = norm_date(date_s), norm_time(start), norm_time(end)
    if s >= e:
        raise ValueError("End time must be after start time")
    return d, s, e


def _conflict(conn, space, date_s, start, end, exclude_id=None):
    sql = ("SELECT booking_id FROM bookings WHERE space=? AND booking_date=? "
           "AND status IN ('Active','Confirmed') AND start_time < ? AND end_time > ?")
    args = [space, date_s, end, start]
    if exclude_id:
        sql += " AND booking_id != ?"
        args.append(exclude_id)
    return conn.execute(sql, args).fetchone()


def _notify(conn, now, booking_id, kind, to_email, subject, body):
    conn.execute("INSERT INTO notifications(created_at,booking_id,kind,to_email,subject,body) VALUES(?,?,?,?,?,?)",
                 (now_str(now), booking_id, kind, to_email, subject, body))


def _close_requests(conn, booking_id):
    conn.execute("UPDATE reschedule_requests SET status='Closed' WHERE booking_id=? "
                 "AND status IN ('Pending','Needs alternative')", (booking_id,))


# ----------------------------------------------------------------------------- availability
def get_booking(booking_id, db=DB_PATH):
    conn = connect(db)
    try:
        r = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def list_bookings(db=DB_PATH, date_s=None):
    conn = connect(db)
    try:
        if date_s:
            rows = conn.execute("SELECT * FROM bookings WHERE booking_date=? ORDER BY start_time, space", (date_s,))
        else:
            rows = conn.execute("SELECT * FROM bookings ORDER BY booking_date, start_time, space")
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_spaces(db=DB_PATH):
    conn = connect(db)
    try:
        return [r["space"] for r in conn.execute("SELECT space FROM spaces ORDER BY space")]
    finally:
        conn.close()


def is_available(space, date_s, start, end, db=DB_PATH, exclude_id=None):
    d, s, e = validate_slot(date_s, start, end)
    conn = connect(db)
    try:
        return _conflict(conn, space, d, s, e, exclude_id) is None
    finally:
        conn.close()


def free_slots(space, date_s, db=DB_PATH):
    """Free windows for a space between DAY_START and DAY_END."""
    conn = connect(db)
    try:
        rows = conn.execute("SELECT start_time,end_time FROM bookings WHERE space=? AND booking_date=? "
                            "AND status IN ('Active','Confirmed') ORDER BY start_time", (space, date_s)).fetchall()
    finally:
        conn.close()
    free, cursor = [], DAY_START
    for r in rows:
        if r["start_time"] > cursor:
            free.append((cursor, r["start_time"]))
        cursor = max(cursor, r["end_time"])
    if cursor < DAY_END:
        free.append((cursor, DAY_END))
    return free


def suggest_alternatives(space, date_s, start, end, db=DB_PATH, limit=3):
    """Other spaces of the same type free at the same time, then later free windows in the same space."""
    d, s, e = validate_slot(date_s, start, end)
    minutes = int((dt(d, e) - dt(d, s)).total_seconds() / 60)
    kind = space.split()[0]
    out = []
    for sp in list_spaces(db):
        if sp != space and sp.split()[0] == kind and is_available(sp, d, s, e, db):
            out.append({"space": sp, "start": s, "end": e})
    for fs, fe in free_slots(space, d, db):
        if int((dt(d, fe) - dt(d, fs)).total_seconds() / 60) >= minutes and fs != s:
            end_alt = (dt(d, fs) + timedelta(minutes=minutes)).strftime("%H:%M")
            out.append({"space": space, "start": fs, "end": end_alt})
    return out[:limit]


# ----------------------------------------------------------------------------- create / import
def _parse_bool(value):
    """Parse CSV booleans without treating the string 'False' as true."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in ("", "0", "false", "no", "n", "off", "nan"):
        return False
    if text in ("1", "true", "yes", "y", "on"):
        return True
    raise ValueError(f"Invalid boolean value '{value}' (use true/false or 1/0)")


def _parse_nonnegative_int(value, field):
    """Accept integer-like CSV values, reject malformed/negative values."""
    if value is None or str(value).strip().lower() in ("", "nan", "none"):
        return 0
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {field} value '{value}' (use a non-negative whole number)")
    if not number.is_integer() or number < 0:
        raise ValueError(f"Invalid {field} value '{value}' (use a non-negative whole number)")
    return int(number)


def create_booking(b, db=DB_PATH):
    """b: dict with REQUIRED fields (+ OPTIONAL). Returns (ok, message)."""
    try:
        d, s, e = validate_slot(b["booking_date"], b["start_time"], b["end_time"])
    except (ValueError, KeyError) as ex:
        return False, str(ex)
    row = {k: b.get(k, OPTIONAL.get(k)) for k in REQUIRED + list(OPTIONAL)}
    if not row["booking_id"] or not row["space"]:
        return False, "booking_id and space are required"
    status = str(row.get("status") or "Active").strip().title()
    if status not in ("Active", "Confirmed"):
        return False, f"Unsupported booking status '{status}'"
    try:
        row["past_bookings"] = _parse_nonnegative_int(row["past_bookings"], "past_bookings")
        row["past_no_shows"] = _parse_nonnegative_int(row["past_no_shows"], "past_no_shows")
        row["lead_days"] = _parse_nonnegative_int(row["lead_days"], "lead_days")
        row["recurring"] = _parse_bool(row["recurring"])
    except ValueError as ex:
        return False, str(ex)
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")           # take the write lock BEFORE checking
        if _conflict(conn, row["space"], d, s, e):
            conn.execute("ROLLBACK")
            return False, "Slot is no longer available"
        try:
            conn.execute(
                "INSERT INTO bookings(booking_id,space,booking_date,start_time,end_time,coordinator_name,"
                "coordinator_email,booker_name,booker_email,team,status,past_bookings,past_no_shows,lead_days,"
                "recurring,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (row["booking_id"], row["space"], d, s, e, row["coordinator_name"], row["coordinator_email"],
                 row["booker_name"], row["booker_email"], row["team"], status,
                 row["past_bookings"], row["past_no_shows"],
                 row["lead_days"], int(row["recurring"]), now_str(datetime.now())))
        except sqlite3.IntegrityError:
            conn.execute("ROLLBACK")
            return False, f"Booking ID {row['booking_id']} already exists"
        conn.execute("INSERT OR IGNORE INTO spaces(space) VALUES(?)", (row["space"],))
        conn.execute("COMMIT")
        return True, "Booking confirmed"
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


def import_bookings(df, db=DB_PATH):
    """Import a calendar-export DataFrame. Returns {'imported': [...], 'rejected': [(id, reason)]}."""
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        return {"imported": [], "rejected": [("-", f"Missing columns: {', '.join(missing)}")]}
    imported, rejected = [], []
    for rec in df.to_dict("records"):
        bid = str(rec.get("booking_id", "")).strip()
        try:
            raw_status = rec.get("status", "Active")
            status = "Active" if raw_status is None or str(raw_status).strip().lower() in ("", "nan", "none") else str(raw_status).strip().title()
            if status not in ("Active", "Confirmed"):
                raise ValueError(f"status '{status}' is not importable")
            if any(str(rec.get(c, "")).strip().lower() in ("", "nan", "none") for c in REQUIRED):
                raise ValueError("missing required value")
            rec["booking_id"] = bid
            rec["status"] = status
            for field in ("past_bookings", "past_no_shows", "lead_days"):
                rec[field] = _parse_nonnegative_int(rec.get(field, OPTIONAL[field]), field)
            rec["recurring"] = _parse_bool(rec.get("recurring", OPTIONAL["recurring"]))
            ok, msg = create_booking(rec, db)
            if ok:
                imported.append(bid)
            else:
                rejected.append((bid, msg))
        except (TypeError, ValueError) as ex:
            rejected.append((bid, str(ex)))
    return {"imported": imported, "rejected": rejected}


# ----------------------------------------------------------------------------- lifecycle
def checkin_window(b):
    start = dt(b["booking_date"], b["start_time"])
    return start - timedelta(hours=OPENS_HOURS), start - timedelta(hours=DEADLINE_HOURS)


def send_reminder(booking_id, subject, body, now, db=DB_PATH):
    """Atomically send one simulated reminder only for an eligible Active booking."""
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
        if not row or row["status"] != "Active":
            conn.execute("ROLLBACK")
            return False, "Only active, unconfirmed bookings can be sent a reminder"
        b = dict(row)
        if b["reminder_sent_at"]:
            conn.execute("ROLLBACK")
            return False, "A reminder has already been sent for this booking"
        opens, deadline = checkin_window(b)
        if now < opens:
            conn.execute("ROLLBACK")
            return False, f"Check-in window opens at {opens.strftime('%H:%M')}"
        if now >= deadline:
            conn.execute("ROLLBACK")
            return False, f"Check-in deadline ({deadline.strftime('%H:%M')}) has passed"
        conn.execute("UPDATE bookings SET reminder_sent_at=?, respond_by=?, updated_at=? WHERE booking_id=?",
                     (now_str(now), now_str(deadline), now_str(now), booking_id))
        _notify(conn, now, booking_id, "reminder", b["booker_email"], subject, body)
        conn.execute("COMMIT")
        return True, f"Reminder sent to {b['booker_email']}. Respond by {deadline.strftime('%H:%M')}."
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def respond(booking_id, action, now, db=DB_PATH, new_slot=None):
    """Simulated booker response: KEEP, CANCEL or RESCHEDULE (new_slot=(date,start,end))."""
    action = action.upper()
    if action == "RESCHEDULE":
        return request_reschedule(booking_id, *new_slot, now, db)
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")
        r = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
        if not r or r["status"] not in LIVE:
            conn.execute("ROLLBACK")
            return False, "Booking is not active"
        if action == "KEEP":
            # KEEP settles the original booking, so any outstanding reschedule
            # approval must be closed to prevent a later approval moving it.
            _close_requests(conn, booking_id)
            conn.execute("UPDATE bookings SET status='Confirmed', updated_at=? WHERE booking_id=?",
                         (now_str(now), booking_id))
            _notify(conn, now, booking_id, "keep", r["coordinator_email"], f"{r['booker_name']} kept {r['space']}",
                    f"{r['booker_name']} confirmed the booking for {r['space']} on {r['booking_date']} {r['start_time']}.")
            msg = "Booking confirmed (KEEP); pending reschedule requests closed"
        elif action == "CANCEL":
            conn.execute("UPDATE bookings SET status='Cancelled', updated_at=? WHERE booking_id=?",
                         (now_str(now), booking_id))
            _close_requests(conn, booking_id)
            _notify(conn, now, booking_id, "cancel", r["coordinator_email"], f"{r['space']} released",
                    f"{r['booker_name']} cancelled. {r['space']} {r['start_time']}-{r['end_time']} is available again.")
            msg = "Booking cancelled; space released immediately"
        else:
            conn.execute("ROLLBACK")
            return False, f"Unknown action {action}"
        conn.execute("COMMIT")
        return True, msg
    finally:
        conn.close()


def request_reschedule(booking_id, new_date, new_start, new_end, now, db=DB_PATH):
    """Create a coordinator approval request for every reschedule.

    Availability is checked for guidance, but a free slot is NOT auto-accepted.
    The original booking remains unchanged until the coordinator approves and
    approve_reschedule() re-checks availability inside its write transaction.
    """
    try:
        d, s, e = validate_slot(new_date, new_start, new_end)
    except ValueError as ex:
        return False, str(ex)
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")
        r = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
        if not r or r["status"] not in LIVE:
            conn.execute("ROLLBACK")
            return False, "Booking is not active"

        # Idempotency: repeated clicks/retries for the same booking reuse the
        # existing pending request rather than creating another approval card.
        existing = conn.execute(
            "SELECT request_id,new_date,new_start,new_end FROM reschedule_requests "
            "WHERE booking_id=? AND status='Pending' ORDER BY request_id DESC LIMIT 1",
            (booking_id,)
        ).fetchone()
        if existing:
            conn.execute("COMMIT")
            return True, (
                f"A reschedule request is already pending (request #{existing['request_id']}). "
                "Your original booking remains active; no duplicate was created."
            )

        available = _conflict(conn, r["space"], d, s, e, exclude_id=booking_id) is None
        cur = conn.execute(
            "INSERT INTO reschedule_requests(booking_id,new_date,new_start,new_end,created_at,status) "
            "VALUES(?,?,?,?,?,'Pending')",
            (booking_id, d, s, e, now_str(now)))
        request_id = cur.lastrowid
        if available:
            detail = "The requested slot is currently available, pending coordinator approval."
        else:
            detail = "The requested slot is currently unavailable; coordinator review is required."
        _notify(conn, now, booking_id, "approval_needed", r["coordinator_email"],
                "Reschedule request awaiting approval",
                f"{r['booker_name']} requested {r['space']} on {d} {s}-{e}. {detail} "
                "The original booking remains active until approval.")
        conn.execute("COMMIT")
        if available:
            return True, f"Request submitted for coordinator approval (request #{request_id}). The original booking remains active."
        return True, f"Requested slot is unavailable. Sent to coordinator for review (request #{request_id}); original booking remains active."
    finally:
        conn.close()


def pending_requests(db=DB_PATH):
    conn = connect(db)
    try:
        rows = conn.execute("SELECT q.*, b.space, b.booker_name, b.booker_email, b.start_time AS cur_start, "
                            "b.end_time AS cur_end, b.booking_date AS cur_date FROM reschedule_requests q "
                            "JOIN bookings b ON b.booking_id=q.booking_id WHERE q.status='Pending' "
                            "ORDER BY q.request_id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def approve_reschedule(request_id, now, db=DB_PATH):
    """Approve = re-check availability inside the transaction, then update. Never overwrites a newer booking."""
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")
        q = conn.execute("SELECT * FROM reschedule_requests WHERE request_id=? AND status='Pending'",
                         (request_id,)).fetchone()
        if not q:
            conn.execute("ROLLBACK")
            return False, "Request not found or already handled"
        r = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (q["booking_id"],)).fetchone()
        if not r or r["status"] not in LIVE:
            conn.execute("UPDATE reschedule_requests SET status='Closed' WHERE request_id=?", (request_id,))
            conn.execute("COMMIT")
            return False, "Original booking is no longer active"
        if _conflict(conn, r["space"], q["new_date"], q["new_start"], q["new_end"], exclude_id=r["booking_id"]):
            conn.execute("UPDATE reschedule_requests SET status='Needs alternative' WHERE request_id=?", (request_id,))
            _notify(conn, now, r["booking_id"], "needs_alternative", r["booker_email"], "Requested slot was taken",
                    "The slot you asked for was booked by someone else. Your original booking is unchanged; please pick another slot.")
            conn.execute("COMMIT")
            return False, "Slot was taken while approval was pending. Original booking retained; booker asked for an alternative"
        conn.execute("UPDATE bookings SET booking_date=?,start_time=?,end_time=?,status='Confirmed',"
                     "reminder_sent_at=NULL,respond_by=NULL,updated_at=? WHERE booking_id=?",
                     (q["new_date"], q["new_start"], q["new_end"], now_str(now), r["booking_id"]))
        conn.execute("UPDATE reschedule_requests SET status='Approved' WHERE request_id=?", (request_id,))
        _notify(conn, now, r["booking_id"], "reschedule_approved", r["booker_email"], "Reschedule approved",
                f"{r['space']} moved to {q['new_date']} {q['new_start']}-{q['new_end']}.")
        conn.execute("COMMIT")
        return True, "Approved after re-checking availability; booking updated"
    finally:
        conn.close()


def reject_reschedule(request_id, now, db=DB_PATH):
    """Reject: original booking stays Active; booker must choose KEEP or CANCEL (no-response policy applies)."""
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")
        q = conn.execute("SELECT * FROM reschedule_requests WHERE request_id=? AND status='Pending'",
                         (request_id,)).fetchone()
        if not q:
            conn.execute("ROLLBACK")
            return False, "Request not found or already handled"
        r = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (q["booking_id"],)).fetchone()
        conn.execute("UPDATE reschedule_requests SET status='Rejected' WHERE request_id=?", (request_id,))
        if r and r["status"] == "Active":
            _, deadline = checkin_window(dict(r))
            respond_by = max(deadline, now + timedelta(minutes=REJECT_GRACE_MIN))
            conn.execute("UPDATE bookings SET reminder_sent_at=COALESCE(reminder_sent_at, ?), respond_by=?, updated_at=? "
                         "WHERE booking_id=? AND status='Active'",
                         (now_str(now), now_str(respond_by), now_str(now), r["booking_id"]))
            _notify(conn, now, r["booking_id"], "reschedule_rejected", r["booker_email"], "Reschedule not possible",
                    f"Your reschedule was rejected. Your original booking is still active. Please reply KEEP or CANCEL by {respond_by.strftime('%H:%M')}.")
        elif r and r["status"] == "Confirmed":
            _notify(conn, now, r["booking_id"], "reschedule_rejected", r["booker_email"], "Reschedule not possible",
                    "Your reschedule was rejected. Your original booking remains confirmed; no further action is needed.")
        conn.execute("COMMIT")
        return True, "Rejected. Original booking retained; booker asked to KEEP or CANCEL"
    finally:
        conn.close()


def process_deadlines(now, db=DB_PATH):
    """Auto-release reminded-but-unconfirmed bookings whose response deadline has passed."""
    released = []
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute("SELECT * FROM bookings WHERE status='Active' AND reminder_sent_at IS NOT NULL "
                            "AND respond_by IS NOT NULL AND respond_by <= ?", (now_str(now),)).fetchall()
        for r in rows:
            conn.execute("UPDATE bookings SET status='Released', updated_at=? WHERE booking_id=?",
                         (now_str(now), r["booking_id"]))
            _close_requests(conn, r["booking_id"])
            body = f"{r['space']} {r['booking_date']} {r['start_time']}-{r['end_time']} was released: no confirmation by {r['respond_by'][-5:]}."
            _notify(conn, now, r["booking_id"], "auto_release", r["coordinator_email"], f"{r['space']} auto-released", body)
            _notify(conn, now, r["booking_id"], "auto_release", r["booker_email"], "Booking released", body)
            released.append(r["booking_id"])
        conn.execute("COMMIT")
    finally:
        conn.close()
    return released


def risk_review_queue(db=DB_PATH, date_s=None):
    """Return only bookings released for no response at T−2 and eligible for coordinator risk review.

    A KEEP response changes the booking to Confirmed, and a CANCEL response
    releases it without setting this flag. Neither enters this queue.
    """
    conn = connect(db)
    try:
        sql = ("SELECT * FROM bookings WHERE status='Released' "
               "AND risk_review_eligible=1")
        args = []
        if date_s:
            sql += " AND booking_date=?"
            args.append(date_s)
        sql += " ORDER BY booking_date,start_time,space"
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def notifications(db=DB_PATH, limit=100):
    conn = connect(db)
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,))]
    finally:
        conn.close()


def counts(db=DB_PATH, date_s=None):
    conn = connect(db)
    try:
        sql, args = "SELECT status, COUNT(*) n FROM bookings", ()
        if date_s:
            sql, args = sql + " WHERE booking_date=?", (date_s,)
        out = {r["status"]: r["n"] for r in conn.execute(sql + " GROUP BY status", args)}
        out["Pending reschedules"] = conn.execute(
            "SELECT COUNT(*) FROM reschedule_requests WHERE status='Pending'").fetchone()[0]
        return out
    finally:
        conn.close()
