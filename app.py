import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time # Add this at the very top of your script
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="BEMS Digital Twin - B Block", layout="wide", initial_sidebar_state="expanded")
# Refresh every 30 seconds to stay in sync with Unity and the Sheet
st_autorefresh(interval=5 * 1000, key="bems_heartbeat")

# --- 2. SECRETS & URLs (Replace with your actual links) ---
# Update these with your exact URLs

WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
RELAY_ID = "bf44d7e214c9e67fa8vhoy" # Your specific Tuya Device ID

# --- 3. DATA LOADING FUNCTION ---
# Remove @st.cache_data entirely for your presentation to get LIVE data


# Replace YOUR_SHEET_ID with your actual ID
SHEET_ID = "1RSHAh23D4NPwNEU9cD5JbsMsYeZVYVTUfG64_4r-zsU"
DIRECT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def load_data():
    try:
        # We add the cache-buster timestamp to ensure Google doesn't send an old version
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        final_url = f"{DIRECT_URL}&v={timestamp}"
        
        df = pd.read_csv(final_url, on_bad_lines='skip', engine='python')
        df.columns = [str(col).strip() for col in df.columns]
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()
# --- 4. RELAY CONTROL FUNCTION ---


def send_relay_command(state):
    params = {
        "action": "control",
        "id": RELAY_ID,
        "value": "true" if state else "false"
    }
    try:
        # Increased timeout from 15 to 30 to prevent the 'Read timed out' error
        response = requests.get(WEB_APP_URL, params=params, timeout=30) 
        if response.status_code == 200:
            st.cache_data.clear() 
            return True
        return False
    except Exception as e:
        st.sidebar.error(f"Control Error: {e}")
        return False
# --- 5. INITIAL DATA FETCH ---
df = load_data()
latest = None
is_active = False

if not df.empty:
    latest = df.iloc[-1]
    # Logic: If Power is > 5W, we consider the relay "ON"
    current_p = float(latest['Power']) if 'Power' in latest else 0.0
    is_active = current_p > 5.0

# --- 6. SIDEBAR CONTROL CENTER ---
st.sidebar.title("🕹️ BEMS Control Panel")
st.sidebar.markdown("---")

# LIVE STATUS INDICATOR
st.sidebar.subheader("Live System Status")
if is_active:
    st.sidebar.success("✅ GRID STATUS: ACTIVE")
    if latest is not None:
        st.sidebar.write(f"Current Load: {latest['Power']} W")
else:
    st.sidebar.error("🚨 GRID STATUS: SHEDDED")
    st.sidebar.write("Non-Essential Loads (ACs) are OFF")

st.sidebar.markdown("---")

# MANUAL OVERRIDE BUTTONS (Always defined here to prevent NameError)

# --- SIDEBAR CONTROL CENTER ---
st.sidebar.subheader("Manual Load Control")
col_on, col_off = st.sidebar.columns(2)

if col_on.button("🟢 RESTORE", use_container_width=True):
    with st.spinner("Restoring Power..."):
        if send_relay_command(True):
            # 1. Clear cache to prepare for new data
            st.cache_data.clear() 
            # 2. Wait for Google Script to finish its 5s post-log
            st.sidebar.success("Relay: ON")
            # 3. Force refresh the UI
          


if col_off.button("🔴 SHED", use_container_width=True):
    if send_relay_command(False):
        st.cache_data.clear()
        st.sidebar.warning("Shedding Command Sent...")
        # No more long sleep here; the 5s refresh will pick up the logs!
            
st.sidebar.markdown("---")
st.sidebar.info("Note: Essential loads (Lights/Fans) are protected.")

# --- 7. MAIN DASHBOARD UI ---
if latest is not None:
    st.title("⚡ BEMS Digital Twin (B-Block Overview)")
    
    # Alert for overheating
    t_val = float(latest['Temp']) if 'Temp' in latest else 0.0
    if t_val > 65: 
        st.error(f"🚨 SYSTEM ALERT: TEMPERATURE AT {t_val}°C")

    # Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Voltage", f"{latest['Voltage']:.1f} V")
    with m2: st.metric("Current", f"{latest['Current']:.2f} A")
    with m3: st.metric("Power", f"{int(latest['Power'])} W")
    with m4: st.metric("Temp", f"{t_val:.1f} °C")
    with m5:
        today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
        st.metric("Energy (Today)", f"{today_kwh:.3f} kWh")

    # Real-time Graph
    st.markdown("### 📈 Live Power Consumption (B-Block)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Timestamp'].tail(50), 
        y=df['Power'].tail(50), 
        mode='lines+markers',
        line=dict(color='#00FF00', width=2),
        fill='tozeroy'
    ))
    fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ Connecting to Digital Twin Data Stream...")
    st.info("Check your Google Sheet CSV Link if this persists.")





