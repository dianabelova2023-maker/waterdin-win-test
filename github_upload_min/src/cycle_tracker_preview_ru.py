from __future__ import annotations

import calendar
from datetime import date

import streamlit as st


st.set_page_config(
    page_title="Cycle Bloom — EN Preview",
    page_icon="🌸",
    layout="wide",
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "name" not in st.session_state:
    st.session_state.name = "Guest"
if "cycle_len" not in st.session_state:
    st.session_state.cycle_len = 28
if "period_len" not in st.session_state:
    st.session_state.period_len = 5
if "last_period_start" not in st.session_state:
    st.session_state.last_period_start = date.today()
if "logs" not in st.session_state:
    st.session_state.logs = []


def add_log(symptom: str, mood: str, note: str) -> None:
    st.session_state.logs.insert(
        0,
        {
            "date": date.today().isoformat(),
            "symptom": symptom,
            "mood": mood,
            "note": note.strip() or "—",
        },
    )


def day_in_cycle() -> int:
    delta = (date.today() - st.session_state.last_period_start).days
    return (delta % st.session_state.cycle_len) + 1


def days_to_next_period() -> int:
    return st.session_state.cycle_len - day_in_cycle()


def render_flower_calendar(current_date: date, cycle_start: date) -> str:
    month_title = calendar.month_name[current_date.month].upper()
    weekday_labels = ["M", "T", "W", "T", "F", "S", "S"]
    cal = calendar.Calendar(firstweekday=0)  # Monday
    weeks = cal.monthdayscalendar(current_date.year, current_date.month)

    rows_html = []
    for week in weeks:
        cells = []
        for idx, day in enumerate(week):
            if day == 0:
                cells.append('<td class="cal-empty"></td>')
                continue

            cls = ["cal-day"]
            if idx >= 5:
                cls.append("weekend")
            cell_date = date(current_date.year, current_date.month, day)

            if day == current_date.day:
                cls.append("today")
            if cycle_start <= cell_date <= current_date:
                cls.append("cycle-mark")

            flower = (
                '<span class="flower">🌸</span>'
                if cycle_start <= cell_date <= current_date
                else ""
            )
            cells.append(
                f'<td class="{" ".join(cls)}"><span class="num">{day}</span>{flower}</td>'
            )
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    header = "".join([f"<th>{d}</th>" for d in weekday_labels])
    return f"""
<div class="pretty-calendar">
  <div class="month-title">{month_title}</div>
  <table>
    <thead><tr>{header}</tr></thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
</div>
"""


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Nunito:wght@400;600;700;800&display=swap');

:root {
    --bg-rose: #fff6fb;
    --bg-peach: #ffeef5;
    --line: #f3cddd;
    --text-main: #4d2d40;
    --text-soft: #6c4a60;
    --accent: #cf5f93;
}

html, body, [class*="css"] {
    font-family: "Nunito", sans-serif;
    color: var(--text-main);
}

h1, h2, h3 {
    font-family: "Playfair Display", serif !important;
    color: var(--text-main) !important;
}

p, li, label, span, div {
    color: var(--text-main);
}

[data-testid="stAppViewContainer"] {
    background:
      radial-gradient(900px 550px at 8% -12%, #ffdceb 0%, transparent 62%),
      radial-gradient(700px 420px at 96% 6%, #ffe9cf 0%, transparent 64%),
      linear-gradient(180deg, var(--bg-rose) 0%, var(--bg-peach) 100%);
}

[data-testid="stHeader"] {
    background: #fff7fbba;
    backdrop-filter: blur(5px);
}

[data-testid="stSidebar"] {
    background: #fff7fb;
}

[data-testid="stMetric"] {
    background: #fff;
    border: 1px solid #efd0dd;
    border-radius: 14px;
}

.hero {
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 22px 22px 14px;
    background: linear-gradient(135deg, #fffafd 0%, #fff2f8 100%);
    box-shadow: 0 16px 45px rgba(218, 133, 166, 0.14);
}

.hero p {
    color: var(--text-soft);
}

.section-card {
    border: 1px solid #efc5d8;
    border-radius: 20px;
    background: #fff;
    padding: 14px;
}

.log-row {
    border: 1px solid #f1d6e1;
    border-radius: 12px;
    background: #fff8fc;
    padding: 8px 10px;
    margin-bottom: 8px;
}

.pretty-calendar {
    border: 1px solid #efc8d9;
    border-radius: 22px;
    padding: 16px;
    background: #fff;
    max-width: 360px;
}

.month-title {
    color: #ef4a43;
    font-weight: 800;
    letter-spacing: 1px;
    margin-bottom: 8px;
    font-size: 1.7rem;
}

.pretty-calendar table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}

.pretty-calendar th {
    text-align: center;
    color: #2d2730;
    font-weight: 800;
    padding: 6px 0 8px;
    font-size: 1.4rem;
}

.pretty-calendar td {
    text-align: center;
    height: 48px;
    vertical-align: middle;
    position: relative;
}

.pretty-calendar .cal-empty {
    color: transparent;
}

.pretty-calendar .num {
    color: #2d2730;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}

.pretty-calendar .weekend .num {
    color: #87808a;
}

.pretty-calendar .today .num {
    color: #fff;
    background: #ff4d47;
    border-radius: 50%;
    display: inline-flex;
    width: 36px;
    height: 36px;
    align-items: center;
    justify-content: center;
}

.pretty-calendar .flower {
    position: absolute;
    right: 8px;
    bottom: 1px;
    font-size: 0.78rem;
    opacity: .85;
}

/* Contrast fixes for Streamlit controls */
input, textarea, [data-baseweb="select"] *, [data-baseweb="input"] * {
    color: #3f2032 !important;
    -webkit-text-fill-color: #3f2032 !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] > div {
    background: #fff !important;
    border: 1px solid #d8b7c6 !important;
}

.stButton > button {
    background: linear-gradient(135deg, #de7ea8, #c85b90) !important;
    color: #fff !important;
    border: 1px solid #b64c80 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
}

.stButton > button * {
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <h1>Cycle Bloom — Interactive Demo Prototype</h1>
</div>
""",
    unsafe_allow_html=True,
)

section = st.sidebar.radio(
    "Section",
    ["Login/Sign up", "Account", "Today", "Calendar", "Articles"],
    index=2 if st.session_state.logged_in else 0,
)

if section == "Login/Sign up":
    st.subheader("Login and Initial Setup")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name", value=st.session_state.name if st.session_state.logged_in else "")
        email = st.text_input("Email", placeholder="name@example.com")
    with c2:
        cycle_len = st.number_input("Cycle length", min_value=20, max_value=40, value=st.session_state.cycle_len)
        period_len = st.number_input("Period length", min_value=2, max_value=10, value=st.session_state.period_len)
    last_period = st.date_input("Last period start date", value=st.session_state.last_period_start)

    if st.button("Save and Sign in", use_container_width=True):
        if not name.strip():
            st.error("Enter your name")
        else:
            st.session_state.logged_in = True
            st.session_state.name = name.strip()
            st.session_state.cycle_len = int(cycle_len)
            st.session_state.period_len = int(period_len)
            st.session_state.last_period_start = last_period
            st.success("Saved. Continue to the Today section.")

elif not st.session_state.logged_in:
    st.warning("Please complete Login/Sign up first.")

elif section == "Today":
    st.subheader(f"Today, {st.session_state.name}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Cycle day", day_in_cycle())
    c2.metric("Until next period", f"{days_to_next_period()} days")
    c3.metric("Log entries", len(st.session_state.logs))

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("**Quick daily log**")
    l1, l2 = st.columns(2)
    with l1:
        symptom = st.selectbox("Symptom", ["No symptoms", "Pain", "Fatigue", "Bloating", "Headache"])
    with l2:
        mood = st.selectbox("Mood", ["Calm", "Normal", "Sensitive", "Irritable"])
    note = st.text_input("Note", placeholder="Example: felt better after a walk")
    if st.button("Add log entry", use_container_width=True):
        add_log(symptom, mood, note)
        st.success("Entry added")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("**Latest entries**")
    if not st.session_state.logs:
        st.info("No entries yet")
    else:
        for row in st.session_state.logs[:6]:
            st.markdown(
                f'<div class="log-row"><b>{row["date"]}</b> · {row["symptom"]} · {row["mood"]}<br>{row["note"]}</div>',
                unsafe_allow_html=True,
            )

elif section == "Calendar":
    st.subheader("Cycle Calendar")
    left, right = st.columns([1, 1.2])
    with left:
        st.markdown(
            render_flower_calendar(date.today(), st.session_state.last_period_start),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.write(f"Today: **day {day_in_cycle()} of {st.session_state.cycle_len}**")
        st.write(f"Until next period: **{days_to_next_period()} days**")
        st.markdown("</div>", unsafe_allow_html=True)

elif section == "Articles":
    st.subheader("Articles")
    for title, desc in [
        ("PMS without panic", "How to track symptoms and reduce discomfort."),
        ("Cycle and nutrition", "Habits that can improve your well-being."),
        ("When to see a doctor", "Red flags you should not ignore."),
    ]:
        st.markdown(
            f'<div class="section-card"><b>{title}</b><br>{desc}<br><span style="color:#a14f76">Open article →</span></div>',
            unsafe_allow_html=True,
        )
        st.write("")

elif section == "Account":
    st.subheader("Account")
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.write(f"Name: **{st.session_state.name}**")
    st.write(f"Cycle length: **{st.session_state.cycle_len}**")
    st.write(f"Period length: **{st.session_state.period_len}**")
    period_reminder = st.toggle("Period reminder", value=True)
    article_reminder = st.toggle("Article reminder", value=True)
    st.caption(
        f"Notification status: period {'on' if period_reminder else 'off'}, articles {'on' if article_reminder else 'off'}."
    )
    if st.button("Log out", use_container_width=True):
        st.session_state.logged_in = False
        st.success("You have logged out.")
    st.markdown("</div>", unsafe_allow_html=True)
