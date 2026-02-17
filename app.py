import streamlit as st
import pandas as pd
import os, json

st.set_page_config(page_title="Attendance Bunk Simulator", layout="centered")

# ========== AUTO SAVE (LOCAL FILE) ==========
AUTO_SAVE_FILE = "user_timetable.json"

def save_user_data(data):
    with open(AUTO_SAVE_FILE, "w") as f:
        json.dump(data, f)

def load_user_data():
    if os.path.exists(AUTO_SAVE_FILE):
        with open(AUTO_SAVE_FILE, "r") as f:
            return json.load(f)
    return {}

# ========== UI ==========
st.title("📅 Attendance Bunk Simulator")

MIN_PERCENT = st.number_input("Minimum required %", 50, 100, 75, 1)

# Tabs
tabs = st.tabs(["📊 Calculator", "📅 Bunk Simulator"])

# ---------- TAB 1: Simple Calculator (Optional) ----------
with tabs[0]:
    st.info("This tab is optional. Use 📅 Bunk Simulator for full features.")
    p = st.number_input("Present", 0, step=1)
    t = st.number_input("Total", 0, step=1)
    if st.button("Calculate %"):
        pct = round((p/t)*100, 2) if t else 0
        st.metric("Attendance %", f"{pct}%")

# ---------- Load saved data at start ----------
saved = load_user_data()
if saved:
    st.session_state.user_subjects = saved.get("subjects", [])
    st.session_state.user_lectures = saved.get("lectures", {})
    st.session_state.user_attendance = saved.get("attendance", {})

# ---------- TAB 2: Bunk Simulator ----------
with tabs[1]:
    st.header("📅 Bunk Simulator — Apna Timetable + Attendance (Auto-Save)")

    default_subjects = ", ".join(st.session_state.get("user_subjects", []))
    default_lectures = ", ".join(str(v) for v in st.session_state.get("user_lectures", {}).values())

    st.subheader("📚 Subjects (comma separated)")
    subjects_input = st.text_area(
        "Example: Physics, EG, FOP, Maths",
        value=default_subjects,
        placeholder="Physics, EG, FOP"
    )

    st.subheader("🗓️ Kal ka Timetable (har subject ke lectures)")
    lectures_input = st.text_area(
        "Example: 2, 1, 1",
        value=default_lectures,
        placeholder="2,1,1"
    )

    cA, cB = st.columns(2)
    with cA:
        if st.button("💾 Save Subjects + Timetable"):
            try:
                subjects = [s.strip() for s in subjects_input.split(",") if s.strip()]
                lectures = [int(x.strip()) for x in lectures_input.split(",") if x.strip()]

                if len(subjects) != len(lectures):
                    st.error("❌ Subjects aur lectures ki count match nahi ho rahi")
                else:
                    st.session_state.user_subjects = subjects
                    st.session_state.user_lectures = dict(zip(subjects, lectures))

                    save_user_data({
                        "subjects": st.session_state.user_subjects,
                        "lectures": st.session_state.user_lectures,
                        "attendance": st.session_state.get("user_attendance", {})
                    })
                    st.success("✅ Subjects + timetable auto-saved!")
            except:
                st.error("❌ Galat format. Example: Physics, EG | 2,1")

    with cB:
        if st.button("🔁 Refresh from saved"):
            saved = load_user_data()
            if saved:
                st.session_state.user_subjects = saved.get("subjects", [])
                st.session_state.user_lectures = saved.get("lectures", {})
                st.session_state.user_attendance = saved.get("attendance", {})
                st.success("🔄 Saved data reload ho gaya!")
            else:
                st.info("ℹ️ Koi saved data nahi mila.")

    if "user_subjects" in st.session_state and st.session_state.user_subjects:
        st.subheader("📊 Apni Current Attendance")

        attendance = {}
        for sub in st.session_state.user_subjects:
            c1, c2 = st.columns(2)
            with c1:
                p = st.number_input(
                    f"{sub} - Present",
                    0, step=1,
                    value=int(st.session_state.get("user_attendance", {}).get(sub, [0, 0])[0]),
                    key=f"p_{sub}"
                )
            with c2:
                t = st.number_input(
                    f"{sub} - Total",
                    0, step=1,
                    value=int(st.session_state.get("user_attendance", {}).get(sub, [0, 0])[1]),
                    key=f"t_{sub}"
                )
            attendance[sub] = (p, t)

        # Auto-save attendance
        st.session_state.user_attendance = attendance
        save_user_data({
            "subjects": st.session_state.user_subjects,
            "lectures": st.session_state.user_lectures,
            "attendance": st.session_state.user_attendance
        })

        st.subheader("📉 Kal bunk karoge toh kya hoga? (Total bunk)")
        bunk_total = st.number_input("Kal total kitne lecture bunk karoge?", 0, 10, 1)

        if st.button("🔮 Simulate Total Bunk"):
            sim_rows = []
            remaining = bunk_total

            for sub in st.session_state.user_subjects:
                lec = int(st.session_state.user_lectures.get(sub, 0))
                p, t = attendance.get(sub, (0, 0))

                bunk_here = min(lec, remaining)
                remaining -= bunk_here

                new_p = p
                new_t = t + bunk_here
                new_pct = round((new_p / new_t) * 100, 2) if new_t else 0

                sim_rows.append([sub, p, t, bunk_here, new_pct])

            sim_df = pd.DataFrame(sim_rows, columns=["Subject", "Present", "Total", "Bunked Tomorrow", "New %"])
            st.dataframe(sim_df, use_container_width=True)

            overall_new = round(sim_df["New %"].mean(), 2)
            st.metric("📉 Overall After Bunk", f"{overall_new}%")

            if overall_new < MIN_PERCENT:
                st.error("🚨 Danger zone! Attendance % low ho jayegi.")
            else:
                st.success("😎 Safe hai.")

        st.divider()
        st.subheader("🎯 Sirf ek subject me bunk")

        sub_sel = st.selectbox("Kaunsa subject bunk karega?", st.session_state.user_subjects)
        bunk_sub_cnt = st.number_input("Us subject me kitne lecture bunk karega?", 0, 5, 1)

        if st.button("🎯 Simulate Subject Bunk"):
            sim_rows = []
            for sub in st.session_state.user_subjects:
                p, t = attendance.get(sub, (0, 0))
                bunk_here = bunk_sub_cnt if sub == sub_sel else 0

                new_p = p
                new_t = t + bunk_here
                new_pct = round((new_p / new_t) * 100, 2) if new_t else 0

                sim_rows.append([sub, p, t, bunk_here, new_pct])

            sim_df = pd.DataFrame(sim_rows, columns=["Subject", "Present", "Total", "Bunked", "New %"])
            st.dataframe(sim_df, use_container_width=True)

            overall_new = round(sim_df["New %"].mean(), 2)
            st.metric("📉 Overall After Subject Bunk", f"{overall_new}%")

            if overall_new < MIN_PERCENT:
                st.error("🚨 Danger zone!")
            else:
                st.success("😎 Safe hai.")

        st.divider()
        if st.button("🧹 Clear Saved Data"):
            try:
                if os.path.exists(AUTO_SAVE_FILE):
                    os.remove(AUTO_SAVE_FILE)
                for k in ["user_subjects", "user_lectures", "user_attendance"]:
                    st.session_state.pop(k, None)
                st.success("🗑️ Data cleared! Page refresh kar lo.")
            except Exception as e:
                st.error(f"❌ Clear failed: {e}")
    else:
        st.info("⬆️ Pehle subjects aur timetable save karo.")
