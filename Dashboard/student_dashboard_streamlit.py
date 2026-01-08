import streamlit as st
import requests
import datetime


st.set_page_config(
    page_title="Student Study Room Dashboard",
    layout="wide"
)

st.title(" Student Study Room Dashboard")
st.caption("Live data from Controller")
st.write("Last update:", datetime.datetime.now())

st.markdown("---")

CONTROLLER_URL = "http://127.0.0.1:18080/"


try:
    response = requests.get(CONTROLLER_URL, timeout=5)
    response.raise_for_status()
    rooms = response.json()
except Exception as e:
    st.error(f" Cannot connect to Controller: {e}")
    st.stop()


if not isinstance(rooms, list) or len(rooms) == 0:
    st.warning(" No room data received from Controller.")
    st.stop()


col1, col2, col3, col4 = st.columns([2, 3, 3, 3])

col1.markdown("**Room ID**")
col2.markdown("**Occupancy**")
col3.markdown("**Temperature (°C)**")
col4.markdown("**Availability**")

st.divider()


for r in rooms:
    room_id = r.get("room_id", "N/A")
    students = r.get("students")
    capacity = r.get("capacity")
    temperature = r.get("temperature")
    available = r.get("available")

    
    if students is not None and capacity:
        occupancy_text = f"{students} / {capacity}"
        occupancy_rate = students / capacity
    else:
        occupancy_text = "N/A"
        occupancy_rate = 0.0

    c1, c2, c3, c4 = st.columns([2, 3, 3, 3])

    
    c1.markdown(f"**{room_id}**")

    
    c2.markdown(occupancy_text)
    c2.progress(min(occupancy_rate, 1.0))

    
    if temperature is None:
        c3.markdown("🌡 N/A")
    else:
        c3.markdown(f"🌡 {temperature:.1f}")

    
    if available:
        c4.markdown("🟢 **Available**")
    else:
        c4.markdown("🔴 **Not Available**")

    st.divider()

st.caption("Dashboard shows all rooms, including occupied ones. No filtering applied.")