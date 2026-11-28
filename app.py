
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Market Basket Analysis Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Market Basket Analysis")
st.subheader("Business Intelligence Dashboard")

st.markdown("""
Explore the Power BI report for retail market basket analysis.
""")

# Your existing Power BI report
report_url = (
    "https://app.powerbi.com/reportEmbed"
    "?reportId=f3b6d1a8-4352-48ce-ac15-9ac82f37b844"
    "&autoAuth=true"
)

st.link_button("Open Dashboard Directly in Power BI", 
               "https://app.powerbi.com/groups/me/reports/"
               "f3b6d1a8-4352-48ce-ac15-9ac82f37b844/"
               "a361debbb237bbac3100?experience=power-bi")

st.divider()

st.markdown("### Power BI Interactive Report")

components.iframe(
    report_url,
    height=800,
    scrolling=True
)

st.caption(
    "Sign in with an account that has permission to view this Power BI report."
)
