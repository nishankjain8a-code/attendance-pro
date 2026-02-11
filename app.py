import streamlit as st
import pandas as pd
import math, random, os
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Attendance Pro Ultimate", layout="centered")

# ========== CONFIG ==========
ADMIN_CODE = "1234"   # <<< CHANGE THIS >>>
SHEET_ID = "1hjP2VZYQJT3nfo6X0s7-p7Wr5Zlvwk7SroSBLTx1gfc"
  # <<< YOUR SHEET ID >>>
SHEET_NAME = "Sheet1"  # <<< CHANGE IF YOUR TAB NAME IS DIFFERENT >>>

# Put your downloaded JSON filename here:
LOCAL_JSON_KEY = "stunning-shadow-480614-r3-e600fa51e8c1.json"  # <<< CHANGE IF NEEDED >>>

SUBJECTS = [
    ("Engineering Physics", "TH", 2),
    ("Engineering Physics", "PR", 1),
    ("Engineering Graphics", "TH", 3),
    ("Engineering Graphics", "PR", 1),
    ("Foundations of Programming", "TH", 3),
    ("Foundations of Programming", "PR", 2),
    ("Discrete Mathematics with Graph Theory", "TH", 3),
    ("Foundations of Computer Architecture and System Design", "TH", 3),
    ("Foundations of Computer Architecture and System Design", "PJ", 1),
    ("Yoga - II", "PR", 1),
    ("Foundations of Peace", "TH", 2),
]

# ========== GOOGLE SHEETS ==========

def get_gsheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(LOCAL_JSON_KEY, scopes=scopes)
    return gspread.authorize(creds)

def get_sheet():
    client = get_gsheet_client()
    sh = client.open_by_key(SHEET_ID)   # <-- safest method
    return sh.worksheet(SHEET_NAME)




def read_leaderboard():
    try:
        ws = get_sheet()
        # Auto-migrate: update header row if student_name column is missing
        header = ws.row_values(1)
        if header and "student_name" not in header:
            new_header = ["nickname","student_name","section","overall_pct","safe_bunks","timestamp","week_id"]
            ws.update("A1:G1", [new_header])
        rows = ws.get_all_records()
        return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"⚠️ Could not read leaderboard: {e}")
        return pd.DataFrame()

def append_leaderboard(row: dict):
    try:
        ws = get_sheet()
        ws.append_row([
            row["nickname"],
            row["student_name"],
            row["section"],
            row["overall_pct"],
            row["safe_bunks"],
            row["timestamp"],
            row["week_id"],
        ])
        return True
    except Exception as e:
        st.error(f"❌ Could not submit to leaderboard: {e}")
        return False

def clear_leaderboard():
    try:
        ws = get_sheet()
        ws.clear()
        ws.append_row(["nickname","student_name","section","overall_pct","safe_bunks","timestamp","week_id"])
        return True
    except Exception as e:
        st.error(f"❌ Could not clear leaderboard: {e}")
        return False

# ========== HELPERS ==========
def pct(p, t): 
    return (p/t*100) if t else 0

def safe_bunks(p, t, minp):
    if t == 0: return 0
    return max(0, math.floor((p/(minp/100)) - t))

def simulate_weeks(p, t, per_week, weeks=2, attend_all=False):
    add = per_week*weeks
    return pct(p + add if attend_all else p, t + add)

def guru(cur, sim, minp, typ):
    if cur >= minp+8: msg = "🔥 Chill hai. 1 bunk/week safe."
    elif cur >= minp: msg = "🙂 Safe zone. Control me bunk."
    else: msg = "🚨 Danger! Next 2 weeks full attend kar."
    if sim < minp: msg += " ❌ Bunk kiya toh limit ke neeche jaoge."
    if typ in ["PR","PJ"]: msg += " 🧪 Practical strict!"
    return msg

# ========== UI ==========
st.title("✨ Attendance Pro — Ultimate")
st.caption("Smart Fill • AI Guru • Leaderboard • Admin Tools")

MIN_PERCENT = st.number_input("Minimum required %", 50, 100, 80, 1)

if "nickname" not in st.session_state:
    animals = ["Falcon","Tiger","Wolf","Panda","Eagle","Fox","Dragon"]
    color_names = ["Red","Blue","Green","Neon","Shadow","Silver","Crimson"]
    st.session_state.nickname = f"{random.choice(color_names)}{random.choice(animals)}{random.randint(10,99)}"

student_name = st.text_input("👤 Your Name", placeholder="Enter your name (e.g. Rahul Sharma)")
section = st.selectbox("Your Section / Division", ["Div 1","Div 2","Div 3","Div 10","Other"])

# ========== INPUT ==========
st.subheader("🧠 Smart Fill")
rows = []
for i, (name, typ, per_week) in enumerate(SUBJECTS):
    with st.expander(f"{name} ({typ})"):
        mode = st.radio("Input mode", ["Enter % only", "Enter Present/Total"], key=f"m{i}", horizontal=True)
        if mode == "Enter % only":
            perc = st.number_input("Your current %", 0.0, 100.0, step=0.5, key=f"pc{i}")
            total = st.number_input("Approx total classes till now", 0, step=1, key=f"tt{i}")
            present = round((perc/100) * total) if total else 0
        else:
            present = st.number_input("Present", 0, step=1, key=f"p{i}")
            total = st.number_input("Total", 0, step=1, key=f"t{i}")
            perc = pct(present, total)
        rows.append((name, typ, present, total, per_week, perc))

# ========== ANALYZE ==========
if st.button("🚀 Analyze"):
    df = pd.DataFrame(rows, columns=["Subject","Type","Present","Total","PerWeek","%"])
    total_safe_bunks = 0
    for _, r in df.iterrows():
        bunks = safe_bunks(int(r["Present"]), int(r["Total"]), MIN_PERCENT)
        total_safe_bunks += bunks
    overall_pct = round(df["%"].mean(), 2) if len(df) else 0
    # Save results in session_state so Submit button works
    st.session_state.analysis_done = True
    st.session_state.analysis_df = df
    st.session_state.overall_pct = overall_pct
    st.session_state.total_safe_bunks = total_safe_bunks

# Show analysis results if available
if st.session_state.get("analysis_done"):
    df = st.session_state.analysis_df
    st.dataframe(df, use_container_width=True)

    for _, r in df.iterrows():
        cur = r["%"]
        sim_bunk = simulate_weeks(int(r["Present"]), int(r["Total"]), int(r["PerWeek"]), weeks=2, attend_all=False)
        sim_attend = simulate_weeks(int(r["Present"]), int(r["Total"]), int(r["PerWeek"]), weeks=3, attend_all=True)

        st.markdown(f"**{r['Subject']} ({r['Type']})**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Current %", f"{cur:.2f}%")
        c2.metric("If bunk 2 weeks", f"{sim_bunk:.2f}%")
        c3.metric("If attend all 3 weeks", f"{sim_attend:.2f}%")
        st.info("🤖 " + guru(cur, sim_bunk, MIN_PERCENT, r["Type"]))

    overall_pct = st.session_state.overall_pct
    st.metric("Overall %", overall_pct)

    # ---------- SUBMIT ----------
    if st.button("🏆 Submit to Leaderboard"):
        if not student_name.strip():
            st.warning("⚠️ Please enter your name above before submitting!")
        else:
            row = {
                "nickname": st.session_state.nickname,
                "student_name": student_name.strip(),
                "section": section,
                "overall_pct": overall_pct,
                "safe_bunks": int(st.session_state.total_safe_bunks),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "week_id": date.today().isocalendar().week
            }
            if append_leaderboard(row):
                st.success(f"✅ Submitted for {student_name.strip()}!")

# ========== MY HISTORY ==========
st.divider()
st.subheader("📜 My History")
history_name = st.text_input("🔍 Search by your name", placeholder="Enter your name to see past entries")
if history_name.strip():
    lb_all = read_leaderboard()
    if len(lb_all) > 0 and "student_name" in lb_all.columns:
        my_history = lb_all[lb_all["student_name"].astype(str).str.lower() == history_name.strip().lower()]
        if len(my_history):
            st.dataframe(
                my_history.sort_values(by="timestamp", ascending=False).reset_index(drop=True),
                use_container_width=True
            )
            st.caption(f"📊 Total submissions: {len(my_history)} | Best overall %: {my_history['overall_pct'].max()}")
        else:
            st.info(f"No history found for '{history_name.strip()}'. Make sure the name matches exactly.")
    else:
        st.info("No leaderboard data yet.")

# ========== PUBLIC LEADERBOARD ==========
st.divider()
st.subheader("🏆 Leaderboard (Filter by Section)")

lb_df = read_leaderboard()
has_data = len(lb_df) > 0 and "overall_pct" in lb_df.columns
if has_data:
    filter_section = st.selectbox("Filter", ["All"] + sorted(lb_df["section"].dropna().unique().tolist()))
    show_df = lb_df if filter_section == "All" else lb_df[lb_df["section"] == filter_section]
    st.dataframe(show_df.sort_values(by=["overall_pct","safe_bunks"], ascending=[False, True]).head(10), use_container_width=True)
else:
    st.info("No entries yet.")

# ========== ADMIN VIEW ==========
st.divider()
st.subheader("🔐 Admin View (Class Rep)")
admin_code_input = st.text_input("Enter admin code", type="password")

if admin_code_input == ADMIN_CODE:
    st.success("Admin access granted ✅")

    st.write("📊 Full Leaderboard")
    st.dataframe(lb_df, use_container_width=True)

    if st.button("📅 Reset leaderboard now (weekly)"):
        clear_leaderboard()
        st.success("Leaderboard reset!")

    st.write("🧾 Export Class Report (PDF)")
    if st.button("Generate PDF"):
        pdf_path = "class_report.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        elems = [Paragraph("Class Attendance Leaderboard Report", styles["Title"]), Spacer(1, 12)]
        table_data = [["Nickname","Section","Overall %","Safe Bunks","Timestamp"]]
        for _, r in (lb_df.sort_values(by=["overall_pct","safe_bunks"], ascending=[False, True]).iterrows() if has_data else []):
            table_data.append([r["nickname"], r["section"], f'{r["overall_pct"]}', f'{r["safe_bunks"]}', r["timestamp"]])
        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),rl_colors.lightgrey),
            ('GRID',(0,0),(-1,-1),0.5,rl_colors.black),
            ('FONT',(0,0),(-1,0),'Helvetica-Bold'),
            ('ALIGN',(2,1),(-1,-1),'CENTER'),
        ]))
        elems.append(t)
        doc.build(elems)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF report", f, file_name="class_report.pdf", mime="application/pdf")

elif admin_code_input:
    st.error("Wrong admin code ❌")
