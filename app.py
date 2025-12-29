import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# 1. DATA LOADING
# Replace with your 'Publish to Web' CSV link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pubhtml"

@st.cache_data(ttl=60) # Refreshes every minute
def load_data():
    df = pd.read_csv(SHEET_URL)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

try:
    df = load_data()
    latest = df.iloc[-1]
    
    # 2. HEADER & LIVE STATS
    st.title("⚡ BEMS Live Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Voltage", f"{latest['Voltage']} V")
    col2.metric("Current", f"{latest['Current']} A")
    col3.metric("Live Power", f"{latest['Power']} W")
    
    # Calculate Today's kWh
    today = datetime.now().date()
    df_today = df[df['Timestamp'].dt.date == today]
    today_kwh = df_today['kWh_Interval'].sum()
    col4.metric("Today's Energy", f"{today_kwh:.2f} kWh", delta_color="inverse")

    st.divider()

    # 3. INTERACTIVE ANALYTICS SECTION
    st.subheader("📊 Historical Analysis & Trends")
    
    # Selection for Time Granularity
    view_option = st.radio(
        "Select Graph Resolution:",
        ["Minute-wise (Raw)", "Hourly Aggregated", "Daily Aggregated"],
        horizontal=True
    )

    # Selection for Parameter
    param_option = st.selectbox("Select Parameter to View:", ["Power (W)", "Voltage (V)", "Current (A)", "kWh"])
    param_map = {"Power (W)": "Power", "Voltage (V)": "Voltage", "Current (A)": "Current", "kWh": "kWh_Interval"}

    # Processing Data based on selection
    if view_option == "Hourly Aggregated":
        plot_df = df.resample('H', on='Timestamp').mean() if param_option != "kWh" else df.resample('H', on='Timestamp').sum()
        plot_df = plot_df.reset_index()
    elif view_option == "Daily Aggregated":
        plot_df = df.resample('D', on='Timestamp').mean() if param_option != "kWh" else df.resample('D', on='Timestamp').sum()
        plot_df = plot_df.reset_index()
    else:
        plot_df = df

    # Plotting
    fig = px.line(plot_df, x='Timestamp', y=param_map[param_option], 
                  title=f"{param_option} - {view_option}",
                  template="plotly_dark")
    
    # Enable range slider for "Swiping" through history
    fig.update_xaxes(rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Waiting for data... Ensure your Sheet is 'Published to Web'. Error: {e}")
