import streamlit as st
import datetime

st.set_page_config(
    page_title="Demo - Test Room Dashboard",
    layout="wide"
)

st.title(" Demo - Test Room Dashboard")
st.caption("Front-end demo only · Not connected to backend")
st.write("Time:", datetime.datetime.now())

st.markdown("---")

st.subheader("🎓 Student View - Test Room (Demo)")

col1, col2, col3, col4 = st.columns([2, 3, 3, 3])
col1.markdown("**Room ID**")
col2.markdown("**Occupancy**")
col3.markdown("**Temperature**")
col4.markdown("**Availability**")

st.divider()

c1, c2, c3, c4 = st.columns([2, 3, 3, 3])
c1.markdown("**TEST_ROOM**")
c2.markdown("— / —")
c3.markdown("🌡 —")
c4.markdown(" Demo only")

st.caption("Student dashboard example · Read-only")

st.markdown("---")

st.subheader(" Manager View - Test Room (Demo)")

col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 3])
col1.markdown("**Room ID**")
col2.markdown("**Status**")
col3.markdown("**Temperature**")
col4.markdown("**Occupancy**")
col5.markdown("**Control**")

st.divider()

m1, m2, m3, m4, m5 = st.columns([2, 2, 3, 2, 3])

m1.markdown("**TEST_ROOM**")
m2.markdown(" Demo")
m3.markdown("🌡 —")
m4.markdown("— / —")

if m5.button("Turn HVAC ON (Demo)"):
    st.info("Demo action only. No command sent to backend.")

st.caption("Manager dashboard example · Control buttons are demo only")

st.markdown("---")

st.markdown("""
 **Important**  
- This page is a **front-end demo only**  
- It does **not** connect to Controller or Catalog  
- It does **not** affect real rooms or HVAC  
- Used only to demonstrate how a *test room* would be displayed
""")