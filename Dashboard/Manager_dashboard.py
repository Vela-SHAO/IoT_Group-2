import streamlit as st
import json
import datetime
import random
import os

st.set_page_config(
    page_title="Smart Campus – Manager Dashboard",
    layout="wide"
)

st.markdown('<meta http-equiv="refresh" content="10">', unsafe_allow_html=True)

st.title("Smart Campus – Manager Dashboard")
st.subheader("Real-time Room Monitoring & Control")

st.write("Now:", datetime.datetime.now())

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "rooms_config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

rooms = config["rooms"]

st.markdown("---")
st.subheader("Global Temperature Control")

mode = st.selectbox(
    "Select HVAC Mode:",
    ["Automatic", "Comfort", "Energy Saving"]
)

if st.button("Apply Mode"):
    st.success(f"Manager command sent: **{mode} mode**")
    st.caption("Command forwarded to control layer via MQTT (logical flow).")


st.markdown("---")
st.subheader("Real-time Room Status")

for r in rooms:
    capacity = r["capacity"]

    people = random.randint(0, capacity)
    temperature = round(random.uniform(19.0, 26.0), 1)
    occupancy_rate = people / capacity if capacity else 0

    col1, col2, col3, col4, col5 = st.columns([2, 2, 4, 2, 2])

    col1.write(f"**Room**: {r['room_id']}")
    col2.write(f"👥 {people} / {capacity}")
    col3.progress(occupancy_rate)
    col4.write(f"{occupancy_rate*100:.1f}%")
    col5.write(f"{temperature} °C")

st.caption(
    "Live dynamic data (mock). "
    "Occupancy & temperature updated every 10 seconds. "
    "Control logic handled by backend services."
)