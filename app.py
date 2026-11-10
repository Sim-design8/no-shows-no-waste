"""No-Shows, No Waste — two-view college MVP.
Booker and coordinator experiences share the tested SQLite booking engine.
CSV is used instead of live calendar integration; notifications are simulated.
"""
import json, os, random
from datetime import date, datetime, time, timedelta
import pandas as pd
import streamlit as st
import booking_engine as be

st.set_page_config(page_title="No-Shows, No Waste", page_icon="🪑", layout="wide")
DB = os.environ.get("NSNW_DB", be.DB_PATH)
be.init_db(DB)
HOST_NAME, HOST_EMAIL = "Facilities Desk", "facilities.desk@example.com"
DEFAULT_MODEL = "gemini-2.5-flash"

# ---------- visual system ----------
st.markdown("""
<style>
:root { --ink:#172554; --muted:#64748b; --blue:#2563eb; --line:#dbeafe; }
.block-container {padding-top:1.5rem; padding-bottom:2rem; max-width:1400px;}
[data-testid="stAppViewContainer"] {background:linear-gradient(135deg,#f7faff 0%,#f8f7ff 100%);}
[data-testid="stSidebar"] {background:#eef4ff;}
.hero {padding:1.1rem 1.4rem;border:1px solid #dbeafe;border-radius:18px;background:#fff;margin-bottom:1rem;}
.hero h1 {color:#172554;font-size:1.8rem;margin:0 0 .25rem 0;}
.hero p {color:#64748b;margin:0;}
.kpi {background:white;border:1px solid #dbeafe;border-radius:15px;padding:1rem;min-height:105px;}
.kpi .n {font-size:1.8rem;font-weight:750;color:#172554;}
.kpi .l {font-size:.85rem;color:#64748b;}
.panel {background:white;border:1px solid #e2e8f0;border-radius:16px;padding:1rem 1.1rem;margin:.5rem 0 1rem 0;}
.pill {display:inline-block;padding:.22rem .65rem;border-radius:99px;font-weight:650;font-size:.82rem;}
.green {background:#dcfce7;color:#166534;} .amber {background:#fef3c7;color:#92400e;} .red {background:#fee2e2;color:#991b1b;} .blue {background:#dbeafe;color:#1d4ed8;}
div.stButton>button {border-radius:10px;font-weight:600;}
</style>
""", unsafe_allow_html=True)

# ---------- demo data ----------
def make_demo_df(day: date, seed: int = 15):
    rng=random.Random(seed)
    names=["Aarav","Meera","Rohan","Ishita","Kabir","Ananya","Vikram","Diya","Arjun","Sana","Neel","Tara","Rahul","Pooja","Yash","Kiara","Dev","Riya","Nikhil","Zoya","Aditya","Mira","Karan","Leela"]
    teams=["Engineering","Sales","Operations","HR","Finance","Design"]
    spaces=[f"Desk D-{n}" for n in range(1,15)]+["Room Everest (8)","Room Kailash (4)","Room Nilgiri (6)","Room Sahyadri (10)"]
    rows=[]
    for i,name in enumerate(names):
        risky=rng.random()<.35; past=rng.randint(4,30)
        ns=rng.randint(max(1,int(past*.3)),max(1,int(past*.6))) if risky else rng.randint(0,max(0,int(past*.15)))
        start=rng.choice(["12:00","12:30","13:00","13:30","14:00","15:00"]) if i<18 else "17:00"
        end=(datetime.strptime(start,"%H:%M")+timedelta(hours=1)).strftime("%H:%M")
        rows.append(dict(booking_id=f"B{100+i}",space=spaces[i%len(spaces)],booking_date=day.isoformat(),start_time=start,end_time=end,
          coordinator_name=HOST_NAME,coordinator_email=HOST_EMAIL,booker_name=name,booker_email=f"{name.lower()}@example.com",team=rng.choice(teams),status="Active",
          past_bookings=past,past_no_shows=ns,lead_days=rng.choice([5,7,10,14]) if risky else rng.choice([0,1,2,3]),recurring=int(risky and rng.random()<.6)))
    return pd.DataFrame(rows)

def seed_demo(day):
    be.reset_db(DB); return be.import_bookings(make_demo_df(day),DB)

# ---------- risk + reminder ----------
def risk(b, now):
    score=0; why=[]
    rate=b['past_no_shows']/b['past_bookings'] if b['past_bookings'] else 0
    score += min(rate,.6)/.6*50
    if rate>=.25: why.append(f"{int(rate*100)}% past no-show rate")
    score += min(b['lead_days'],14)/14*20
    if b['lead_days']>=7: why.append(f"Booked {b['lead_days']} days ahead")
    if b['recurring']: score+=10; why.append("Recurring booking")
    opens,_=be.checkin_window(b)
    if b['status']=="Active" and now>=opens: score+=20; why.append("Not confirmed in check-in window")
    score=int(round(min(score,100)))
    return score, ("High" if score>=60 else "Medium" if score>=35 else "Low"), why

SYSTEM_INSTRUCTION="""Write one friendly, concise email body (max 70 words) from a workplace coordinator to an employee. Mention only supplied booking details and deadline. Ask them to reply KEEP, RESCHEDULE or CANCEL. Explain that no response by the deadline releases the booking automatically. Never mention risk scores or blame the employee. Return only the message."""
def reminder_text(b, deadline, api_key, model):
    p={"booker_name":b['booker_name'],"space":b['space'],"date":b['booking_date'],"start":b['start_time'],"deadline":deadline.strftime('%H:%M'),"host":b['coordinator_name']}
    fallback=(f"Hi {p['booker_name']}, please confirm {p['space']} on {p['date']} at {p['start']}. Reply KEEP, RESCHEDULE or CANCEL. Without a reply by {p['deadline']}, the booking will be released. — {p['host']}")
    if not api_key: return fallback,"Template (no API key)"
    try:
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=api_key)
        out=client.models.generate_content(model=model,contents=json.dumps(p),config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION,temperature=.3,max_output_tokens=180))
        return (out.text or fallback).strip(),f"Gemini · {model}"
    except Exception as ex: return fallback,f"Template fallback · {type(ex).__name__}"

# ---------- sidebar controls ----------
with st.sidebar:
    st.markdown("## 🪑 No-Shows, No Waste")
    view=st.radio("Choose your view",["Booker (Employee)","Coordinator (Facilities)"],index=0)
    st.divider()
    demo_day=st.date_input("Demo date",value=date.today())
    demo_clock=st.time_input("Demo clock",value=time(9,30))
    now=datetime.combine(demo_day,demo_clock)
    st.caption("Confirmation window: opens 3 hours before booking; deadline is 2 hours before.")
    if view.startswith("Coordinator"):
        try:
            key_default = st.secrets["GEMINI_API_KEY"]
        except Exception:
            key_default = os.environ.get("GEMINI_API_KEY", "")
        api_key=st.text_input("Gemini API key (optional)",value=key_default,type="password")
        model=st.text_input("Gemini model",DEFAULT_MODEL)
        st.divider()
        upload=st.file_uploader("Import calendar CSV",type=["csv"])
        if upload and st.button("Import bookings from CSV",use_container_width=True):
            try:
                report=be.import_bookings(pd.read_csv(upload),DB)
                st.session_state.notice=f"Imported {len(report['imported'])}; rejected {len(report['rejected'])}."
            except Exception as e: st.session_state.notice=f"CSV error: {e}"
            st.rerun()
        st.download_button("Download CSV template",make_demo_df(demo_day).head(3).to_csv(index=False),"bookings_template.csv","text/csv",use_container_width=True)
        if st.button("Reset demo data",use_container_width=True):
            report=seed_demo(demo_day); st.session_state.notice=f"Loaded {len(report['imported'])} synthetic bookings."; st.rerun()
    else:
        api_key=""; model=DEFAULT_MODEL
    st.divider()
    st.caption("Prototype: CSV calendar input and simulated emails. Demo data is synthetic.")

if not be.list_bookings(DB): seed_demo(demo_day)
released=be.process_deadlines(now,DB)
all_rows=be.list_bookings(DB)
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))
if released: st.warning("Automatically released at deadline: "+", ".join(released))

# ---------- booker experience ----------
if view.startswith("Booker"):
    st.markdown('<div class="hero"><h1>👋 Booker workspace</h1><p>Book a space, keep your plans up to date, and release rooms you no longer need.</p></div>',unsafe_allow_html=True)
    emails=sorted({b['booker_email'] for b in all_rows if b.get('booker_email')})
    selected_email=st.selectbox("Demo employee · requester email",emails,index=0 if emails else None,help="Choose a synthetic employee to preview their personal booking experience.")
    my=[b for b in all_rows if b['booker_email']==selected_email]
    active=sum(b['status'] in be.LIVE for b in my)
    pending=sum(bool(b['reminder_sent_at']) and b['status']=="Active" for b in my)
    cols=st.columns(3)
    for col,n,l in zip(cols,[len(my),active,pending],["My bookings","Active bookings","Awaiting my response"]):
        col.markdown(f'<div class="kpi"><div class="n">{n}</div><div class="l">{l}</div></div>',unsafe_allow_html=True)
    left,right=st.columns([1,1.2],gap="large")
    with left:
        st.markdown("### ＋ Book a space")
        with st.form("booker_new_booking",clear_on_submit=True):
            person=st.text_input("Your name",value=next((b['booker_name'] for b in my),"Demo Employee"))
            email=st.text_input("Your email",value=selected_email or "employee@example.com")
            book_date=st.date_input("Booking date",value=demo_day,key="book_date")
            spaces=be.list_spaces(DB) or ["Desk D-1"]
            space=st.selectbox("Choose a space",spaces)
            c1,c2=st.columns(2); start=c1.text_input("Start (HH:MM)","10:00"); end=c2.text_input("End (HH:MM)","11:00")
            submit=st.form_submit_button("Check availability & confirm",use_container_width=True)
            if submit:
                ok,msg=be.create_booking(dict(booking_id=f"B{random.randint(1000,9999)}",space=space,booking_date=book_date.isoformat(),start_time=start,end_time=end,
                  coordinator_name=HOST_NAME,coordinator_email=HOST_EMAIL,booker_name=person,booker_email=email,team="-"),DB)
                if ok: st.session_state.notice=f"Booking confirmed: {space}, {book_date}, {start}–{end}."; st.rerun()
                st.error(msg)
                try:
                    alts=be.suggest_alternatives(space,book_date.isoformat(),start,end,DB)
                    if alts: st.info("Try instead: "+" · ".join(f"{x['space']} {x['start']}–{x['end']}" for x in alts))
                except ValueError: pass
    with right:
        st.markdown("### My booking status")
        if not my: st.info("No bookings for this requester yet.")
        for b in sorted(my,key=lambda x:(x['booking_date'],x['start_time'])):
            with st.container(border=True):
                st.markdown(f"**{b['space']}**  ·  {b['booking_date']}  ·  {b['start_time']}–{b['end_time']}")
                st.caption(f"Booking {b['booking_id']} · Host: {b['coordinator_name']} · Status: {b['status']}")
                if b['status'] in be.LIVE:
                    if b['reminder_sent_at']:
                        st.warning(f"Reminder received · Please respond by {b['respond_by'][-5:] if b['respond_by'] else 'the deadline'}")
                    a,bcol,cc=st.columns(3)
                    if a.button("✓ KEEP",key=f"keep_{b['booking_id']}",use_container_width=True):
                        ok,msg=be.respond(b['booking_id'],"KEEP",now,DB); st.session_state.notice=msg; st.rerun()
                    if bcol.button("↗ RESCHEDULE",key=f"res_{b['booking_id']}",use_container_width=True): st.session_state[f"show_res_{b['booking_id']}"]=not st.session_state.get(f"show_res_{b['booking_id']}",False)
                    if cc.button("✕ CANCEL",key=f"cancel_{b['booking_id']}",use_container_width=True):
                        ok,msg=be.respond(b['booking_id'],"CANCEL",now,DB); st.session_state.notice=msg; st.rerun()
                    if st.session_state.get(f"show_res_{b['booking_id']}",False):
                        with st.form(f"res_form_{b['booking_id']}"):
                            nd=st.date_input("New date",value=demo_day,key=f"nd_{b['booking_id']}")
                            x,y=st.columns(2); ns=x.text_input("New start","14:00",key=f"ns_{b['booking_id']}"); ne=y.text_input("New end","15:00",key=f"ne_{b['booking_id']}")
                            if st.form_submit_button("Submit reschedule request"):
                                ok,msg=be.respond(b['booking_id'],"RESCHEDULE",now,DB,new_slot=(nd.isoformat(),ns,ne))
                                st.session_state.notice=msg; st.rerun()
                elif b['status'] in ("Released","Cancelled"):
                    st.caption("This space is available for another employee to book.")
    st.markdown("### What happens after a reminder?")
    st.markdown('<div class="panel"><b>KEEP</b> · Retain booking &nbsp;&nbsp; <b>RESCHEDULE</b> · Check new slot availability &nbsp;&nbsp; <b>CANCEL</b> · Release immediately &nbsp;&nbsp; <b>NO RESPONSE</b> · Auto-release at deadline</div>',unsafe_allow_html=True)

# ---------- coordinator experience ----------
else:
    st.markdown('<div class="hero"><h1>Facilities coordinator</h1><p>Monitor booking activity, intervene on at-risk spaces, and recover capacity before it goes to waste.</p></div>',unsafe_allow_html=True)
    today=[b for b in all_rows if b['booking_date']==demo_day.isoformat()]
    counts=be.counts(DB,demo_day.isoformat())
    risk_rows=[]
    for b in today:
        if b['status']=="Active":
            s,band,why=risk(b,now); risk_rows.append({**b,"risk":s,"band":band,"reason":" · ".join(why) or "No strong risk signals"})
    high=sum(x['band']=="High" for x in risk_rows); medium=sum(x['band']=="Medium" for x in risk_rows)
    reclaimed=counts.get("Released",0)+counts.get("Cancelled",0)
    kpis=[(len(today),"Bookings today"),(high+medium,"At-risk bookings"),(reclaimed,"Spaces recovered"),(counts.get("Pending reschedules",0),"Reschedule approvals")]
    cols=st.columns(4)
    for col,(n,label) in zip(cols,kpis): col.markdown(f'<div class="kpi"><div class="n">{n}</div><div class="l">{label}</div></div>',unsafe_allow_html=True)
    tab1,tab2,tab3,tab4=st.tabs(["Overview & bookings","Risk & reminders","Reschedule approvals","Notification log"])
    with tab1:
        st.markdown("### Today's bookings")
        if today:
            df=pd.DataFrame(today); df['time']=df.start_time+"–"+df.end_time
            st.dataframe(df[["booking_id","space","time","coordinator_name","booker_name","booker_email","status"]].rename(columns={"coordinator_name":"Host","booker_name":"Requester","booker_email":"Requester email"}),use_container_width=True,hide_index=True)
        else: st.info("No bookings for the selected demo date.")
        st.markdown("### Booking status")
        # Present status totals as readable KPI cards instead of rendering a raw dict.
        status_counts = [(label, value) for label, value in counts.items()
                         if label != "Pending reschedules"]
        if status_counts:
            status_cols = st.columns(min(4, len(status_counts)))
            for idx, (label, value) in enumerate(status_counts):
                with status_cols[idx % len(status_cols)]:
                    st.metric(label=label, value=value)
        else:
            st.caption("No booking status data for this date yet.")
    with tab2:
        st.caption("Risk is a transparent heuristic to prioritise coordinator attention; it does not itself cancel bookings.")
        if risk_rows:
            rq=pd.DataFrame(risk_rows).sort_values("risk",ascending=False)
            st.dataframe(rq[["booking_id","booker_name","booker_email","space","start_time","risk","band","reason","reminder_sent_at"]],use_container_width=True,hide_index=True,
              column_config={"risk":st.column_config.ProgressColumn("Risk score",min_value=0,max_value=100,format="%d")})
            candidates=[r for r in risk_rows if r['band']!="Low" and not r['reminder_sent_at']]
            if candidates:
                st.markdown("### Send a confirmation reminder")
                labels={b['booking_id']:f"{b['booking_id']} · {b['booker_name']} · {b['space']} · {b['start_time']} · {b['band']} ({b['risk']})" for b in candidates}
                chosen=st.selectbox("Select booking",list(labels),format_func=labels.get)
                bsel=be.get_booking(chosen,DB); _,deadline=be.checkin_window(bsel)
                st.caption(f"To: {bsel['booker_email']}  ·  From: {bsel['coordinator_email']}  ·  Deadline: {deadline:%H:%M}")
                if st.button("✨ Draft reminder",type="primary"):
                    body,source=reminder_text(bsel,deadline,api_key,model); st.session_state[f"draft_{chosen}"]=(body,source)
                if f"draft_{chosen}" in st.session_state:
                    body,source=st.session_state[f"draft_{chosen}"]; st.caption(source)
                    edited=st.text_area("Review reminder before sending",body,key=f"edit_{chosen}")
                    subject=f"Please confirm your booking for {bsel['space']}"
                    if st.button("Send reminder (simulated)"):
                        ok,msg=be.send_reminder(chosen,subject,edited,now,DB)
                        if ok: st.session_state.notice=msg; st.rerun()
                        st.error(msg)
            else: st.info("No medium/high-risk bookings awaiting reminders. Adjust the demo clock to simulate the confirmation window.")
        else: st.info("No active bookings for this date.")
    with tab3:
        pending=be.pending_requests(DB)
        if not pending: st.info("No reschedule requests awaiting coordinator review.")
        for q in pending:
            with st.container(border=True):
                st.markdown(f"**{q['booker_name']}** ({q['booker_email']}) · {q['space']}")
                st.write(f"Original: {q['cur_date']} {q['cur_start']}–{q['cur_end']}  →  Requested: {q['new_date']} {q['new_start']}–{q['new_end']}")
                a,b=st.columns(2)
                if a.button("Approve after availability re-check",key=f"approve_{q['request_id']}",use_container_width=True):
                    ok,msg=be.approve_reschedule(q['request_id'],now,DB); st.session_state.notice=msg; st.rerun()
                if b.button("Reject request",key=f"reject_{q['request_id']}",use_container_width=True):
                    ok,msg=be.reject_reschedule(q['request_id'],now,DB); st.session_state.notice=msg; st.rerun()
    with tab4:
        notifications=be.notifications(DB)
        st.caption("All messages are simulated. No email is actually sent.")
        if notifications: st.dataframe(pd.DataFrame(notifications)[["created_at","kind","to_email","subject","body"]],use_container_width=True,hide_index=True)
        else: st.info("No notifications yet.")

with st.expander("Prototype scope & transparency"):
    st.markdown("- Coordinator is the booking host; booker email identifies the requester.\n- CSV substitutes for Outlook/Google Calendar integration.\n- Email notifications are simulated; no real messages are sent.\n- Risk score is rule-based; Gemini only drafts reminder text.\n- SQLite is used for this college prototype; production would need persistent hosted storage, authentication and calendar/email integrations.\n- All seeded demo people and bookings are synthetic.")
