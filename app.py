import streamlit as st
import pandas as pd
import math, random, os, io
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw

st.set_page_config(page_title="Attendance Pro Ultimate", layout="centered")

# ===== CONFIG =====
def get_config(key, default):
    if "app_config" in st.secrets and key in st.secrets["app_config"]:
        return st.secrets["app_config"][key]
    return default

ADMIN_CODE = get_config("admin_code", "1234")
SHEET_ID = get_config("sheet_id", "1hjP2VZYQJT3nfo6X0s7-p7Wr5Zlvwk7SroSBLTx1gfc")
SHEET_NAME = get_config("sheet_name", "Sheet1")
LOCAL_JSON_KEY = "stunning-shadow-480614-r3-e600fa51e8c1.json"

SUBJECTS = [
    ("Engineering Physics", "TH", 2), ("Engineering Physics", "PR", 1),
    ("Engineering Graphics", "TH", 3), ("Engineering Graphics", "PR", 1),
    ("Foundations of Programming", "TH", 3), ("Foundations of Programming", "PR", 2),
    ("Discrete Mathematics with Graph Theory", "TH", 3),
    ("Foundations of Computer Architecture and System Design", "TH", 3),
    ("Foundations of Computer Architecture and System Design", "PJ", 1),
    ("Yoga - II", "PR", 1), ("Foundations of Peace", "TH", 2),
]

# ===== GOOGLE SHEETS =====
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    if os.path.exists(LOCAL_JSON_KEY):
        creds = Credentials.from_service_account_file(LOCAL_JSON_KEY, scopes=scopes)
    else:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

def get_sheet():
    client = get_gsheet_client()
    sh = client.open_by_key(SHEET_ID)
    return sh.worksheet(SHEET_NAME)

def read_leaderboard():
    try:
        ws = get_sheet()
        header = ws.row_values(1)
        if header and "student_name" not in header:
            ws.update("A1:G1", [["nickname","student_name","section","overall_pct","safe_bunks","timestamp","week_id"]])
        return pd.DataFrame(ws.get_all_records())
    except Exception as e:
        st.error(f"⚠️ Leaderboard Error: {e}")
        return pd.DataFrame()

def append_leaderboard(row):
    try:
        ws = get_sheet()
        ws.append_row([row["nickname"], row["student_name"], row["section"], row["overall_pct"],
                       row["safe_bunks"], row["timestamp"], row["week_id"]])
        return True
    except Exception as e:
        st.error(f"❌ Submission Error: {e}")
        return False

def clear_leaderboard():
    try:
        ws = get_sheet()
        ws.clear()
        ws.append_row(["nickname","student_name","section","overall_pct","safe_bunks","timestamp","week_id"])
        return True
    except Exception as e:
        st.error(f"❌ Reset Error: {e}")
        return False

# ===== AUTO-RESET =====
def check_weekly_reset():
    cur_week = date.today().isocalendar().week
    meta_path = "meta.csv"
    last_week = 0
    if os.path.exists(meta_path):
        try:
            mdf = pd.read_csv(meta_path)
            last_week = int(mdf.iloc[0]["last_reset_week"])
        except: pass
    if cur_week > last_week:
        if clear_leaderboard():
            pd.DataFrame([{"last_reset_week": cur_week}]).to_csv(meta_path, index=False)
            return True
    return False

# ===== HELPERS =====
def pct(p,t): return (p/t*100) if t else 0
def safe_bunks(p,t,minp): return max(0,int((p/(minp/100))-t)) if t else 0
def simulate_weeks(p,t,w,weeks=2,attend_all=False):
    add=w*weeks; return pct(p+add if attend_all else p, t+add)
def guru(cur, sim, minp, typ):
    msg="🔥 Chill hai" if cur>=minp+8 else "🙂 Borderline" if cur>=minp else "🚨 Danger"
    if sim<minp: msg+=" ❌ Bunk mat kar"
    if typ in ["PR","PJ"]: msg+=" 🧪 Practical strict"
    return msg
def risk_meter(cur,minp):
    return ("🟢 SAFE",1.0) if cur>=minp+8 else ("🟡 BORDERLINE",0.6) if cur>=minp else ("🔴 DANGER",0.2)
def end_sem_predictor(p,t,w,weeks_left=6):
    ft=t+w*weeks_left; fp=p+w*weeks_left; return (fp/ft*100) if ft else 0
def bunk_budget(p,t,minp): return max(0,int((p/(minp/100))-t)) if t else 0
def xp_and_level(streak): xp=streak*10; return xp, min(10, xp//50+1)
def badges(overall,bunks,streak):
    out=[]
    if overall>=90: out.append("🥇 No Bunk King")
    if overall>=80 and streak>=5: out.append("🧠 Comeback Kid")
    if bunks==0: out.append("💤 Serial Bunker")
    return out

# ===== UI SETUP =====
st.title("✨ Attendance Pro — Ultimate")

# Restore Premium Styling
st.markdown("""
    <style>
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #00d4ff; }
    .stExpander { border-radius: 10px !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255, 255, 255, 0.05); 
        border-radius: 5px 5px 0 0; 
        padding: 5px 15px;
    }
    </style>
    """, unsafe_allow_html=True)

if check_weekly_reset():
    st.toast("📅 New week detected! Leaderboard has been reset.", icon="🌞")
MIN_PERCENT = st.number_input("Minimum required %", 50, 100, 80, 1)

if "nickname" not in st.session_state:
    st.session_state.nickname = f"User{random.randint(100,999)}"

student_name = st.text_input("👤 Your Name")
section = st.selectbox("Section", ["Div 1","Div 2","Div 3","Div 10","Other"])

tabs = st.tabs([
    "📊 Calculator", "🤖 AI Guru", "🏆 Leaderboard + Admin", "📜 History + 👥 Compare",
    "🚦 Risk Meter", "🔮 End-Sem Predictor", "💸 Bunk Budget",
    "🎮 Streak + 🏅 Badges", "🔥 Heatmap", "📸 Share Card"
])

# ===== TAB 1: Calculator =====
with tabs[0]:
    rows=[]
    for i,(name,typ,w) in enumerate(SUBJECTS):
        with st.expander(f"{name} ({typ})"):
            p=st.number_input("Present",0,step=1,key=f"p{i}")
            t=st.number_input("Total",0,step=1,key=f"t{i}")
            rows.append((name,typ,p,t,w,pct(p,t)))
    if st.button("Analyze"):
        df=pd.DataFrame(rows,columns=["Subject","Type","Present","Total","PerWeek","%"])
        st.session_state.df=df
        st.session_state.overall=round(df["%"].mean(),2) if len(df) else 0
        st.success("Analysis done!")

# ===== TAB 2: AI Guru =====
with tabs[1]:
    if "df" in st.session_state:
        for _,r in st.session_state.df.iterrows():
            sim_bunk=simulate_weeks(int(r["Present"]),int(r["Total"]),int(r["PerWeek"]),2,False)
            st.info(f"{r['Subject']}: {guru(r['%'], sim_bunk, MIN_PERCENT, r['Type'])}")
    else:
        st.info("Run analysis first.")

# ===== TAB 3: Leaderboard + Admin =====
with tabs[2]:
    lb_df=read_leaderboard()
    st.dataframe(lb_df.sort_values(by=["overall_pct","safe_bunks"],ascending=[False,True]).head(10))
    if st.button("Submit to Leaderboard"):
        if "overall" in st.session_state and "df" in st.session_state and student_name.strip():
            bunks=sum(safe_bunks(int(r["Present"]),int(r["Total"]),MIN_PERCENT) for _,r in st.session_state.df.iterrows())
            res = append_leaderboard({
                "nickname": st.session_state.nickname,
                "student_name": student_name.strip(),
                "section": section,
                "overall_pct": st.session_state.overall,
                "safe_bunks": bunks,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "week_id": date.today().isocalendar().week
            })
            if res: st.success("🚀 Score submitted successfully!")
        else:
            st.warning("⚠️ Please run analysis and enter your name first!")
    if st.text_input("Admin Code", type="password")==ADMIN_CODE:
        if st.button("Reset leaderboard"): clear_leaderboard()

# ===== TAB 4: History + Compare =====
with tabs[3]:
    lb_df=read_leaderboard()
    if not lb_df.empty:
        name_q=st.text_input("🔍 Search your history by Name")
        if name_q.strip():
            me=lb_df[lb_df["student_name"].astype(str).str.lower()==name_q.strip().lower()]
            if not me.empty:
                st.dataframe(me.sort_values("timestamp", ascending=False), use_container_width=True)
            else:
                st.info("No records found for this name.")
        
        if len(lb_df["nickname"].unique()) >= 2:
            st.divider()
            st.subheader("👥 Compare with Friends")
            users=lb_df["nickname"].unique().tolist()
            c1, c2 = st.columns(2)
            u1=c1.selectbox("You",users, index=0)
            u2=c2.selectbox("Friend",users, index=min(1, len(users)-1))
            
            d1=lb_df[lb_df["nickname"]==u1].tail(10)
            d2=lb_df[lb_df["nickname"]==u2].tail(10)
            
            fig,ax=plt.subplots(figsize=(8,4))
            fig.patch.set_facecolor('#0e1117')
            ax.set_facecolor('#0e1117')
            ax.plot(d1["overall_pct"].tolist(), marker="o", label=u1, color="#00d4ff")
            ax.plot(d2["overall_pct"].tolist(), marker="o", label=u2, color="#ff4b4b")
            ax.set_title("Attendance Trend", color="white")
            ax.tick_params(colors='white')
            ax.legend()
            st.pyplot(fig)
    else:
        st.info("Leaderboard is currently empty.")

# ===== TAB 5: Risk Meter =====
with tabs[4]:
    if "overall" in st.session_state:
        label,prog=risk_meter(st.session_state.overall, MIN_PERCENT)
        st.progress(prog); st.write(label)
    else:
        st.info("Run analysis first.")

# ===== TAB 6: End-Sem Predictor =====
with tabs[5]:
    if "df" in st.session_state:
        pred=end_sem_predictor(int(st.session_state.df["Present"].sum()),
                               int(st.session_state.df["Total"].sum()),
                               int(st.session_state.df["PerWeek"].sum()))
        st.metric("Predicted End-Sem %", f"{pred:.2f}%")
    else:
        st.info("Run analysis first.")

# ===== TAB 7: Bunk Budget =====
with tabs[6]:
    if "df" in st.session_state:
        bunks=sum(safe_bunks(int(r["Present"]),int(r["Total"]),MIN_PERCENT) for _,r in st.session_state.df.iterrows())
        st.success(f"🎟️ Safe bunks: {bunks}")
    else:
        st.info("Run analysis first.")

# ===== TAB 8: Streak + Badges =====
with tabs[7]:
    streak=random.randint(1,7)
    xp,lvl=xp_and_level(streak)
    st.metric("🔥 Streak", streak); st.metric("⭐ XP", xp); st.metric("🏆 Level", lvl)
    if "overall" in st.session_state:
        bunks=sum(safe_bunks(int(r["Present"]),int(r["Total"]),MIN_PERCENT) for _,r in st.session_state.df.iterrows())
        for b in badges(st.session_state.overall,bunks,streak): st.success(b)

# ===== TAB 9: Heatmap (REALISTIC from leaderboard) =====
with tabs[8]:
    lb_df=read_leaderboard()
    if len(lb_df):
        # simulate realistic pattern from submission times (hour)
        lb_df["hour"] = pd.to_datetime(lb_df["timestamp"], errors="coerce").dt.hour
        lb_df["day"] = pd.to_datetime(lb_df["timestamp"], errors="coerce").dt.dayofweek
        heat = np.zeros((6,2), dtype=int)
        for _,r in lb_df.dropna(subset=["hour","day"]).iterrows():
            day = int(min(r["day"],5))
            col = 0 if r["hour"] < 13 else 1
            heat[day][col] += 1
        fig,ax=plt.subplots()
        ax.imshow(heat, cmap="RdYlGn_r")
        ax.set_xticks([0,1]); ax.set_xticklabels(["Morning","Afternoon"])
        ax.set_yticks(range(6)); ax.set_yticklabels(["Mon","Tue","Wed","Thu","Fri","Sat"])
        st.pyplot(fig)
        st.caption("Based on real submission timestamps (proxy for class time).")
    else:
        st.info("Not enough data for heatmap.")

# ===== TAB 10: Share Card =====
with tabs[9]:
    if "overall" in st.session_state:
        img=Image.new("RGB",(900,450),(20,20,20)); d=ImageDraw.Draw(img)
        d.text((40,40), f"🔥 Attendance: {st.session_state.overall:.2f}%", fill=(255,255,255))
        buf=io.BytesIO(); img.save(buf, format="PNG")
        st.download_button("⬇️ Download Share Card", buf.getvalue(), "attendance_card.png", "image/png")
    else:
        st.info("Run analysis first.")
