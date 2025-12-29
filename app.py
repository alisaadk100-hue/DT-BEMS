import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. PAGE SETUP
st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# This line automatically refreshes the page every 60 seconds
st_autorefresh(interval=60 * 1000, key="datarefresh")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=30)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', skip_blank_lines=True, engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

try:
    df = load_data()
    latest = df.iloc[-1]
    
    # 2. CALCULATIONS
    today = datetime.now().date()
    today_kwh = df[df['Timestamp'].dt.date == today]['kWh_Interval'].sum()
    
    # Nominal Voltage Calibration (Pakistan Standard: 240V)
    v_nominal = 240.0
    v_diff = latest['Voltage'] - v_nominal

    # --- TOP SECTION: LIVE STATUS ---
    st.title("⚡ BEMS Digital Twin: Real-Time Monitor")
    st.write(f"Last Cloud Sync: {latest['Timestamp'].strftime('%H:%M:%S')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Voltage", f"{latest['Voltage']} V", delta=f"{v_diff:.1f} V (Ref: 240V)")
    c2.metric("Current", f"{latest['Current']} A")
    c3.metric("Live Power", f"{latest['Power']} W")
    c4.metric("Today's Energy", f"{today_kwh:.3f} kWh")

    st.divider()

    # --- MIDDLE SECTION: MULTI-METRIC GRAPHS ---
    st.subheader("📊 Interactive Engineering Charts")
    
    # Create a selection for the user
    metric_choice = st.radio("Select Metric to View History:", 
                             ["Power (W)", "Voltage (V)", "Current (A)", "Energy (kWh)"], 
                             horizontal=True)

    # Dictionary to map choices to columns
    mapping = {
        "Power (W)": {"col": "Power", "color": "#00ff00", "title": "Real-Time Power Consumption"},
        "Voltage (V)": {"col": "Voltage", "color": "#ff3333", "title": "Grid Voltage Stability"},
        "Current (A)": {"col": "Current", "color": "#3399ff", "title": "Load Current Draw"},
        "Energy (kWh)": {"col": "kWh_Interval", "color": "#ffaa00", "title": "Energy Slices (per min)"}
    }
    
    selected = mapping[metric_choice]

    # Main Interactive Graph
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Timestamp'], 
        y=df[selected['col']], 
        name=metric_choice,
        line=dict(color=selected['color'], width=2),
        fill='tozeroy' if metric_choice != "Voltage (V)" else None
    ))
    
    # Add a horizontal line for the 240V reference if Voltage is selected
    if metric_choice == "Voltage (V)":
        fig.add_hline(y=240, line_dash="dash", line_color="white", annotation_text="240V Nominal")

    fig.update_layout(
        title=selected['title'],
        xaxis_rangeslider_visible=True, # The "Swipe" feature
        template="plotly_dark",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- BOTTOM SECTION: AGGREGATED STATS ---
    st.subheader("📅 Consumption Summaries")
    tab_h, tab_d = st.tabs(["Hourly Units", "Daily History"])
    
    with tab_h:
        h_df = df.resample('H', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
        st.bar_chart(h_df, x='Timestamp', y='kWh_Interval', color="#3399ff")
        
    with tab_d:
        d_df = df.resample('D', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
        st.bar_chart(d_df, x='Timestamp', y='kWh_Interval', color="#ffaa00")

except Exception as e:
    st.error("System Refreshing... Check Connection.")
    st.info(f"Technical Log: {e}")
