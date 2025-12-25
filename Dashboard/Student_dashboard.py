import streamlit as st
import json
import datetime
import random
import os

st.set_page_config(
    page_title="Smart Campus - Student Dashboard",
    layout="wide"
)

st.markdown('<meta http-equiv="refresh" content="10">', unsafe_allow_html=True)


st.title("Smart Campus - Student Dashboard")
st.subheader(" Study Room Recommendation")

st.write(" Now:", datetime.datetime.now())

# Finding the document's relative path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "rooms_config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

rooms = config["rooms"]


room_status = []

for r in rooms:
    capacity = r["capacity"]
    people = random.randint(0, capacity)
    occupancy_rate = people / capacity if capacity else 0

    room_status.append({
        "room_id": r["room_id"],
        "type": r["type"],
        "capacity": capacity,
        "people": people,
        "rate": occupancy_rate
    })

#Ranking by occupancy_rate
room_status.sort(key=lambda x: x["rate"])


st.markdown(" Recommended Rooms (Top 3)")

for r in room_status[:3]:
    rate = r["rate"]

    if rate < 0.3:
        status = "🟢 Free"
    elif rate < 0.7:
        status = "🟡 Moderate"
    else:
        status = "🔴 Crowded"

    reasons = []
    if rate < 0.3:
        reasons.append("Low occupancy")
    if r["capacity"] >= 200:
        reasons.append("Large capacity")
    if rate < 0.5 and r["capacity"] >= 150:
        reasons.append("Stable occupancy conditions")

#Typesetting requirements
    col1, col2, col3 = st.columns([4, 2, 6])

    col1.markdown(f"**Room: {r['room_id']}** ({r['type']})")
    col2.markdown(f"👥 {r['people']} / {r['capacity']}")
    col3.progress(rate)

    st.caption(f"{status} | Why recommended: " + " · ".join(reasons))
    st.markdown("---")

st.caption("Data refresh every 10 seconds (student view, mock data)")
