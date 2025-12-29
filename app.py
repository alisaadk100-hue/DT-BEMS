import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# 1. Update this with your NEW .csv link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=10)
def load_data():
    # Reading CSV directly from the published link
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', skip_blank_lines=True)
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

try:
    df = load_data()
    latest = df.iloc[-1]
    
    # Calculate Today's Energy
    today = datetime.now().date()
    today_kwh = df[df['Timestamp'].dt.date == today]['kWh_Interval'].sum()

    # --- TOP SECTION: LIVE STATUS ---
    st.title("⚡ BEMS Digital Twin: Online")
    
    # Professional Metric Display
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Voltage", f"{latest['Voltage']} V", delta=f"{latest['Voltage']-230:.1f}V from nominal")
    m2.metric("Load Current", f"{latest['Current']} A")
    m3.metric("Active Power", f"{latest['Power']} W")
    m4.metric("Today's Consumption", f"{today_kwh:.3f} kWh")

    st.divider()

    # --- MIDDLE SECTION: INTERACTIVE TABS ---
    # This creates the "Drill-down" experience you asked for
    tab1, tab2, tab3 = st.tabs(["🚀 Real-time Data", "📅 Hourly Trends", "📈 Daily History"])

    with tab1:
        st.subheader("High-Resolution Power Pulse (1-Min)")
        fig1 = go.Figure(go.Scatter(x=df['Timestamp'], y=df['Power'], 
                                   mode='lines+markers', fill='tozeroy', 
                                   line=dict(color='#00ff00', width=2)))
        fig1.update_layout(xaxis_rangeslider_visible=True, template="plotly_dark", height=500)
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Hourly Energy Aggregation")
        # Summing the 1-minute intervals into 1-hour blocks
        hourly_df = df.resample('H', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
        fig2 = go.Figure(go.Bar(x=hourly_df['Timestamp'], y=hourly_df['kWh_Interval'], marker_color='#3399ff'))
        fig2.update_layout(xaxis_rangeslider_visible=True, template="plotly_dark", height=500)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Daily Historical Units")
        daily_df = df.resample('D', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
        fig3 = go.Figure(go.Bar(x=daily_df['Timestamp'], y=daily_df['kWh_Interval'], marker_color='#ffaa00'))
        fig3.update_layout(xaxis_rangeslider_visible=True, template="plotly_dark", height=500)
        st.plotly_chart(fig3, use_container_width=True)

except Exception as e:
    st.error("🔗 Connection Error: Check your 'Publish to Web' link")
    st.write("Ensure you selected 'Comma-separated values (.csv)' when publishing.")
    st.info(f"Technical Note: {e}")

