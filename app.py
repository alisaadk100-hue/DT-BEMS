import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. THE AUTO-REFRESH (Every 30 seconds) ---
# This forces the website to update on its own
st_autorefresh(interval=30 * 1000, key="bems_heartbeat")

st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# --- 2. DATA SOURCE ---
# Update this with your CSV link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

df = load_data()
latest = df.iloc[-1]

# --- 3. NOMINAL CALCULATIONS (Pakistan 240V Standard) ---
v_actual = float(latest['Voltage'])
v_nominal = 240.0
v_delta = v_actual - v_nominal

# --- 4. LIVE METRICS ---
st.title("⚡ BEMS Digital Twin: Live Feed")
st.write(f"**Last Update:** {latest['Timestamp'].strftime('%H:%M:%S')} | **Refresh:** 30s")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Voltage", f"{v_actual} V", delta=f"{v_delta:.1f} V (Ref: 240)")
c2.metric("Current", f"{latest['Current']} A")
c3.metric("Live Power", f"{latest['Power']} W")

today = datetime.now().date()
today_kwh = df[df['Timestamp'].dt.date == today]['kWh_Interval'].sum()
c4.metric("Today's kWh", f"{today_kwh:.4f}")

st.divider()

# --- 5. MULTI-PARAMETER GRAPHS ---
st.subheader("📊 Interactive Engineering Analysis")
# User selects which parameter to see on the graph
param = st.radio("Select Metric to Graph:", ["Power", "Voltage", "Current"], horizontal=True)

fig = go.Figure()

if param == "Voltage":
    fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Voltage'], name="Voltage", line=dict(color="red")))
    # Visual line for 240V standard
    fig.add_hline(y=240, line_dash="dash", line_color="white", annotation_text="240V Nominal")
elif param == "Power":
    fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Power'], name="Power", fill='tozeroy', line=dict(color="green")))
elif param == "Current":
    fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Current'], name="Current", line=dict(color="blue")))

fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=True, height=500)
st.plotly_chart(fig, use_container_width=True)
