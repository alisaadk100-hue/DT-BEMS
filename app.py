import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Set page to wide mode and dark theme
st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# 1. SETUP
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pubhtml"

@st.cache_data(ttl=30) # Refresh every 30 seconds
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', skip_blank_lines=True)
    df.columns = df.columns.str.strip() # Remove accidental spaces
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

try:
    df = load_data()
    
    # CALCULATIONS
    latest = df.iloc[-1]
    today = datetime.now().date()
    df_today = df[df['Timestamp'].dt.date == today]
    today_kwh = df_today['kWh_Interval'].sum()

    # --- TOP SECTION: LIVE INTERACTIVE CARDS ---
    st.title("⚡ BEMS: Live Digital Twin")
    
    # We use columns for the clean, "app-like" look
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Live Voltage", f"{latest['Voltage']} V")
    c2.metric("Live Current", f"{latest['Current']} A")
    c3.metric("Live Power", f"{latest['Power']} W")
    # This shows today's consumption specifically
    c4.metric("Today's Units", f"{today_kwh:.4f} kWh", delta="Today")

    st.divider()

    # --- MIDDLE SECTION: HISTORICAL DRILL-DOWN ---
    st.subheader("📊 Interactive Consumption History")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["🕒 Real-time (1-Min)", "📅 Hourly Stats", "📈 Daily History"])

    with tab1:
        # Minute-wise graph with range slider (swiping)
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['Timestamp'], y=df['Power'], fill='tozeroy', name='Power (W)'))
        fig1.update_layout(title="Live Power Pulse", xaxis_rangeslider_visible=True, template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        # Hourly Aggregation
        hourly_df = df.resample('H', on='Timestamp').agg({'Power':'mean', 'kWh_Interval':'sum'}).reset_index()
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=hourly_df['Timestamp'], y=hourly_df['kWh_Interval'], name='kWh'))
        fig2.update_layout(title="Hourly Energy Consumption", xaxis_rangeslider_visible=True, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        # Daily Aggregation
        daily_df = df.resample('D', on='Timestamp').agg({'Power':'mean', 'kWh_Interval':'sum'}).reset_index()
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=daily_df['Timestamp'], y=daily_df['kWh_Interval'], name='Total Daily kWh'))
        fig3.update_layout(title="Daily Energy Usage", xaxis_rangeslider_visible=True, template="plotly_dark")
        st.plotly_chart(fig3, use_container_width=True)

    # --- BOTTOM SECTION: DATA TABLE ---
    with st.expander("See Raw Data Log"):
        st.dataframe(df.sort_values(by='Timestamp', ascending=False), use_container_width=True)

except Exception as e:
    st.error("⚠️ Dashboard Sync Error")
    st.info("Check if your Google Sheet has headers: Timestamp, Voltage, Current, Power, Temp, kWh_Interval")
    # Show the actual error for debugging
    st.write(f"Technical Details: {e}")
