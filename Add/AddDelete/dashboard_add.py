import streamlit as st
import requests
import datetime
import time

CATALOG_URL = "http://127.0.0.1:8080/api/devices"
REFRESH_SECONDS = 5

st.set_page_config(
    page_title="Demo - Dynamic Device Dashboard",
    layout="wide"
)

st.markdown(
    f"<meta http-equiv='refresh' content='{REFRESH_SECONDS}'>",
    unsafe_allow_html=True
)

st.title(" Demo - Dynamic Test Room Dashboard")
st.caption("Connected to Catalog · Auto device discovery")
st.write("Last refresh:", datetime.datetime.now())

st.markdown("---")


try:
    resp = requests.get(CATALOG_URL, timeout=5)
    resp.raise_for_status()
    devices = resp.json()
except Exception as e:
    st.error(f"Cannot connect to Catalog: {e}")
    st.stop()

if not devices:
    st.warning("No devices registered in Catalog.")
    st.stop()


rooms = {}

for d in devices:
    room = d.get("location", {}).get("room", "UNKNOWN")
    rooms.setdefault(room, []).append(d)


st.subheader("🎓 Student View (Auto-discovered rooms)")

col1, col2, col3 = st.columns([3, 4, 5])
col1.markdown("**Room ID**")
col2.markdown("**Sensors**")
col3.markdown("**MQTT Topics**")

st.divider()

for room, devs in sorted(rooms.items()):
    sensor_list = []
    topic_list = []

    for d in devs:
        if "val" in d.get("mqtt_topics", {}):
            sensor_list.append(d["id"])
            topic_list.append(d["mqtt_topics"]["val"])

    c1, c2, c3 = st.columns([3, 4, 5])
    c1.markdown(f"**{room}**")
    c2.markdown(", ".join(sensor_list) if sensor_list else "—")
    c3.markdown("<br>".join(topic_list), unsafe_allow_html=True)

st.caption("Student dashboard · Devices appear automatically when registered")

st.markdown("---")


st.subheader(" Manager View (Actuators discovered)")

col1, col2, col3 = st.columns([3, 5, 4])
col1.markdown("**Room ID**")
col2.markdown("**Actuators**")
col3.markdown("**Command Topic**")

st.divider()

for room, devs in sorted(rooms.items()):
    actuators = []
    cmd_topics = []

    for d in devs:
        if "cmd" in d.get("mqtt_topics", {}):
            actuators.append(d["id"])
            cmd_topics.append(d["mqtt_topics"]["cmd"])

    m1, m2, m3 = st.columns([3, 5, 4])
    m1.markdown(f"**{room}**")
    m2.markdown(", ".join(actuators) if actuators else "—")
    m3.markdown("<br>".join(cmd_topics), unsafe_allow_html=True)

st.caption("Manager dashboard · Control wiring visible (demo only)")

st.markdown("---")

st.markdown("""
**What this demo proves**
- ✔ New room appears automatically  
- ✔ New sensor / actuator appears automatically  
- ✔ No hard-coded TEST_ROOM  
- ✔ Frontend reflects Catalog state in real time  

This is a **real dynamic test-room demo**, not a mock.
""")