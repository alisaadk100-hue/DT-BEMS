import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. AUTO-REFRESH (Every 30 seconds)
st_autorefresh(interval=30 * 1000, key="bems_refresh")

st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# 2. DATA CONNECTION
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" # <--- ENSURE THIS ENDS IN output=csv

@st.cache_data(ttl=10)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

try:
    df = load_data()
    latest = df.iloc[-1]
    
    # Calibration
    v_nominal = 240.0
    v_actual = float(latest['Voltage'])
    v_delta = v_actual - v_nominal

    # 3. INTERFACE
    st.title("⚡ BEMS Digital Twin (Live)")
    st.write(f"**Last Update:** {latest['Timestamp']} | **Status:** Connected")

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Voltage", f"{v_actual} V", delta=f"{v_delta:.1f} V (Nom: 240)")
    m2.metric("Current", f"{latest['Current']} A")
    m3.metric("Power", f"{latest['Power']} W")
    
    today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
    m4.metric("Today's kWh", f"{today_kwh:.4f}")

    st.divider()

    # 4. INDIVIDUAL GRAPHS (The Radio Selector)
    st.subheader("📊 Metric History")
    choice = st.radio("Switch Graph:", ["Voltage", "Power", "Current"], horizontal=True)
    
    fig = go.Figure()
    if choice == "Voltage":
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Voltage'], name="Voltage", line=dict(color="#FF4B4B")))
        fig.add_hline(y=240, line_dash="dash", line_color="white", annotation_text="240V Standard")
    elif choice == "Power":
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Power'], fill='tozeroy', name="Power", line=dict(color="#00CC96")))
    else:
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Current'], name="Current", line=dict(color="#636EFA")))

    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=True, height=450)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Syncing Error: {e}")
