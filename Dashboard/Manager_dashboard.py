import streamlit as st
import requests
import datetime


st.set_page_config(
    page_title="Smart Campus - Manager Dashboard",
    layout="wide"
)

st.markdown('<meta http-equiv="refresh" content="10">', unsafe_allow_html=True)

st.title("Smart Campus - Manager Dashboard")
st.subheader("Real-time Room Monitoring & Control")
st.write("Now:", datetime.datetime.now())


CONTROLLER_URL = "http://127.0.0.1:18080/"


try:
    resp = requests.get(CONTROLLER_URL, timeout=5)
    resp.raise_for_status()
    rooms = resp.json()
except Exception as e:
    st.error(f"Cannot connect to Controller: {e}")
    st.stop()

if not isinstance(rooms, list) or len(rooms) == 0:
    st.warning("No room data available from Controller yet.")
    st.stop()


st.markdown("---")
st.subheader("Global HVAC Control")

mode = st.selectbox(
    "Select HVAC Mode:",
    ["Automatic", "Comfort", "Energy Saving"]
)

if st.button("Apply Mode"):
    st.success(f"Manager command sent: **{mode} mode**")
    st.caption("Command would be forwarded to Controller (future work).")


st.markdown("---")
st.subheader("Real-time Room Status")

for r in rooms:
    room_id = r.get("room_id", "-")
    capacity = r.get("capacity", 0)
    students = r.get("students")
    temperature = r.get("temperature")
    available = r.get("available")

    occupancy_rate = (
        students / capacity if students is not None and capacity else 0
    )

    col1, col2, col3, col4, col5 = st.columns([2, 2, 4, 2, 2])

    col1.markdown(f"**Room {room_id}**")

    if students is None:
        col2.markdown("👥 N/A")
        col3.progress(0.0)
        col4.markdown("N/A")
    else:
        col2.markdown(f"👥 {students} / {capacity}")
        col3.progress(min(occupancy_rate, 1.0))
        col4.markdown(f"{occupancy_rate*100:.1f}%")

    if temperature is None:
        col5.markdown("🌡 N/A")
    else:
        col5.markdown(f"🌡 {temperature} °C")

    if available:
        st.markdown("🟢 **Available**")
    else:
        st.markdown("🔴 **Occupied / Not available**")

    st.divider()

st.caption(
    "Live data from Controller (rooms_info). "
    "Auto-refresh every 10 seconds."
)