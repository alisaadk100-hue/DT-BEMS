import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# Replace with your 'Publish to Web' CSV link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pubhtml"

@st.cache_data(ttl=60)
def load_data():
    # 'on_bad_lines' skips the row that caused your error
    # 'skip_blank_lines' ignores those empty rows at the bottom
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', skip_blank_lines=True, engine='python')
    
    # Clean up column names and convert time
    df.columns = df.columns.str.strip()
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    
    # Drop rows where timestamp or power is missing
    df = df.dropna(subset=['Timestamp', 'Power'])
    return df

try:
    df = load_data()
    latest = df.iloc[-1]
    
    # --- SECTION 1: LIVE INTERACTIVE METRICS ---
    st.title("⚡ BEMS Digital Twin: Live Feed")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Live Voltage", f"{latest['Voltage']} V")
    m2.metric("Live Current", f"{latest['Current']} A")
    m3.metric("Live Power", f"{latest['Power']} W")
    
    # Calculate Today's Energy
    today_mask = df['Timestamp'].dt.date == datetime.now().date()
    today_kwh = df.loc[today_mask, 'kWh_Interval'].sum()
    m4.metric("Today's Total", f"{today_kwh:.2f} kWh")

    st.divider()

    # --- SECTION 2: INTERACTIVE DRILL-DOWN ---
    st.subheader("📊 Historical Energy Analysis")
    
    # User selects the "View"
    view_mode = st.radio("Resolution:", ["Real-time (Minutes)", "Hourly Stats", "Daily History"], horizontal=True)
    
    # Aggregation Logic
    if view_mode == "Hourly Stats":
        plot_df = df.resample('H', on='Timestamp').agg({'Power':'mean', 'kWh_Interval':'sum'}).reset_index()
        y_axis = 'kWh_Interval'
    elif view_mode == "Daily History":
        plot_df = df.resample('D', on='Timestamp').agg({'Power':'mean', 'kWh_Interval':'sum'}).reset_index()
        y_axis = 'kWh_Interval'
    else:
        plot_df = df
        y_axis = 'Power'

    # Interactive Plotly Graph
    fig = px.area(plot_df, x='Timestamp', y=y_axis, 
                  title=f"{view_mode} Consumption Pattern",
                  template="plotly_dark", color_discrete_sequence=['#00CC96'])
    
    # This enables the "Swiping/Zooming" functionality
    fig.update_xaxes(rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("Dashboard is updating... Please wait 30 seconds.")
    st.info(f"Technical Note: {e}")
