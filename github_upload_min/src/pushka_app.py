import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Pushka Prototype", page_icon="🪙", layout="centered")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "goal" not in st.session_state:
    st.session_state.goal = 36.0
if "balance" not in st.session_state:
    st.session_state.balance = 0.0
if "presets" not in st.session_state:
    st.session_state.presets = [1.0, 5.0, 10.0]
if "history" not in st.session_state:
    st.session_state.history = []


def add_coin(amount: float):
    st.session_state.balance += amount
    st.session_state.history.insert(0, {
        "time": datetime.now().strftime("%d.%m %H:%M"),
        "amount": amount,
        "type": "coin",
    })


def empty_pushka():
    if st.session_state.balance <= 0:
        return
    payout = st.session_state.balance
    st.session_state.balance = 0.0
    st.session_state.history.insert(0, {
        "time": datetime.now().strftime("%d.%m %H:%M"),
        "amount": payout,
        "type": "payout",
    })


st.markdown(
    """
<style>
.mobile-wrap {
  max-width: 390px;
  margin: 0 auto;
  border-radius: 24px;
  padding: 18px 16px 28px;
  background: linear-gradient(180deg, #f7f8fb 0%, #ffffff 100%);
  box-shadow: 0 10px 40px rgba(10, 25, 62, .10);
  border: 1px solid #eef1f7;
}
.title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: .2px;
  color: #111827;
  margin-bottom: 0;
}
.subtitle {
  color: #4b5563;
  margin-top: 4px;
  margin-bottom: 14px;
}
.cylinder {
  width: 190px;
  height: 300px;
  margin: 10px auto 14px;
  border-radius: 88px 88px 36px 36px;
  border: 3px solid #d1d5db;
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, #f9fafb 0%, #eef2f7 100%);
}
.fill {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  background: linear-gradient(180deg, #76b6ff 0%, #2a6adf 100%);
  transition: height .45s ease;
}
.metrics {
  display: flex;
  justify-content: space-between;
  font-weight: 700;
  color: #2a4f93;
}
.history-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #eff2f6;
}
</style>
    """,
    unsafe_allow_html=True,
)

st.title("Pushka MVP")
st.caption("Черновой мобильный прототип в браузере")

if not st.session_state.logged_in:
    st.markdown('<div class="mobile-wrap">', unsafe_allow_html=True)
    st.markdown('<p class="title">Sign Up or Log In</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Email + Password (MVP)</p>', unsafe_allow_html=True)

    email = st.text_input("Email", placeholder="you@example.com")
    password = st.text_input("Password", type="password")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Войти", use_container_width=True):
            if email and password:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.warning("Заполни email и пароль")
    with col_b:
        if st.button("Demo вход", use_container_width=True):
            st.session_state.logged_in = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

progress = 0.0
if st.session_state.goal > 0:
    progress = min(st.session_state.balance / st.session_state.goal, 1.0)

st.markdown('<div class="mobile-wrap">', unsafe_allow_html=True)
st.markdown('<p class="title">My Pushka</p>', unsafe_allow_html=True)
if st.session_state.balance <= 0:
    st.markdown('<p class="subtitle">Your Pushka is Empty</p>', unsafe_allow_html=True)
else:
    st.markdown('<p class="subtitle">Fill it up!</p>', unsafe_allow_html=True)

st.markdown(
    f'<div class="metrics"><span>Goal: ${st.session_state.goal:.2f}</span><span>${st.session_state.balance:.2f}</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="cylinder"><div class="fill" style="height:{progress*100:.1f}%"></div></div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
for col, amount in zip((c1, c2, c3), st.session_state.presets):
    with col:
        if st.button(f"${amount:.2f}", use_container_width=True):
            add_coin(amount)
            st.rerun()

other = st.number_input("Other", min_value=0.0, step=1.0, format="%.2f")
if st.button("Add Other", use_container_width=True):
    if other > 0:
        add_coin(other)
        st.rerun()

r1, r2 = st.columns(2)
with r1:
    disabled = st.session_state.balance < st.session_state.goal
    if st.button("Donate now", disabled=disabled, use_container_width=True):
        empty_pushka()
        st.success("Вывод средств выполнен")
        st.rerun()
with r2:
    if st.button("Empty pushka", use_container_width=True):
        st.session_state.balance = 0.0
        st.rerun()

with st.expander("Settings"):
    new_goal = st.number_input("Pushka goal", min_value=1.0, value=float(st.session_state.goal), step=1.0)
    p1 = st.number_input("Preset 1", min_value=0.5, value=float(st.session_state.presets[0]), step=0.5)
    p2 = st.number_input("Preset 2", min_value=0.5, value=float(st.session_state.presets[1]), step=0.5)
    p3 = st.number_input("Preset 3", min_value=0.5, value=float(st.session_state.presets[2]), step=0.5)
    if st.button("Save settings", use_container_width=True):
        st.session_state.goal = float(new_goal)
        st.session_state.presets = [float(p1), float(p2), float(p3)]
        st.success("Сохранено")
        st.rerun()

with st.expander("Auto refill"):
    freq = st.radio("Frequency", ["Weekly", "Monthly"], horizontal=True)
    day = st.selectbox("Recurring day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    auto_amount = st.number_input("Amount", min_value=1.0, value=100.0, step=1.0)
    st.button("Save auto refill", use_container_width=True)
    st.caption(f"Draft: {freq} / {day} / ${auto_amount:.2f}")

with st.expander("Reminders"):
    st.toggle("Before Candle Lighting", value=False)
    st.toggle("Streak Reminder", value=True)

st.subheader("My Giving History")
if st.session_state.history:
    for item in st.session_state.history[:10]:
        sign = "+" if item["type"] == "coin" else "-"
        st.markdown(
            f'<div class="history-row"><span>{item["time"]}</span><span>{sign}${item["amount"]:.2f}</span></div>',
            unsafe_allow_html=True,
        )
else:
    st.caption("История пока пустая")

if st.button("Log out"):
    st.session_state.logged_in = False
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
