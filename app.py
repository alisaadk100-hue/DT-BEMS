import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIG & REFRESH ---
st.set_page_config(page_title="BEMS Digital Twin", layout="wide", initial_sidebar_state="expanded")
# Reduced to 15 seconds to match Unity's polling speed
st_autorefresh(interval=15 * 1000, key="bems_heartbeat")

# --- SECRETS & URLs ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
RELAY_ID = "bf44d7e214c9e67fa8vhoy" # Your specific Tuya Device ID

# --- DATA LOADING ---
@st.cache_data(ttl=10) # Reduced TTL for fresher data
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python', header=0)
        df.columns = [str(col).strip() for col in df.columns]
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame()

# --- CONTROL FUNCTION ---
def send_relay_command(state):
    params = {
        "action": "control",
        "id": RELAY_ID,
        "value": "true" if state else "false"
    }
    try:
        response = requests.get(WEB_APP_URL, params=params, timeout=15)
        if response.status_code == 200:
            # FORCE REFRESH: This clears the 15-second cache immediately
            st.cache_data.clear() 
            return True
        return False
    except Exception as e:
        st.error(f"Control Error: {e}")
        return False

# In your Sidebar:
if col_off.button("🔴 SHED", use_container_width=True):
    with st.spinner("Executing Shedding..."): # Visual feedback for the 2-second delay
        if send_relay_command(False):
            st.sidebar.warning("Relay: OFF")
            st.rerun() # Forces the app to reload and show the 0W state
# --- LOAD DATA ---
df = load_data()
if not df.empty:
    latest = df.iloc[-1]
    # Logic: If Power is > 5W, we assume it's ON
    current_p = float(latest['Power']) if 'Power' in latest else 0.0
    is_active = current_p > 5.0
else:
    latest = None
    is_active = False

# --- SIDEBAR CONTROL CENTER ---
st.sidebar.title("🕹️ BEMS Control")
st.sidebar.markdown("---")

# --- NEW: LIVE STATUS INDICATOR ---
st.sidebar.subheader("Live System Status")
if is_active:
    st.sidebar.success("✅ GRID STATUS: ACTIVE")
    st.sidebar.write(f"Current Load: {current_p} W")
else:
    st.sidebar.error("🚨 GRID STATUS: SHEDDED")
    st.sidebar.write("Non-Essential Loads are OFF")

st.sidebar.markdown("---")
st.sidebar.subheader("Manual Override")
col_on, col_off = st.sidebar.columns(2)

if col_on.button("🟢 RESTORE", use_container_width=True):
    if send_relay_command(True):
        st.sidebar.success("Command Sent: ON")
        st.cache_data.clear() # Force refresh data
    
if col_off.button("🔴 SHED", use_container_width=True):
    if send_relay_command(False):
        st.sidebar.warning("Command Sent: OFF")
        st.cache_data.clear() # Force refresh data

st.sidebar.markdown("---")
st.sidebar.subheader("Safety Protocol")
st.sidebar.info("Essential Loads (Fans/Lights) are locked to ON.")

# --- APP LOGIC (REST OF YOUR CODE) ---
if 'page' not in st.session_state: st.session_state.page = 'Home'

if latest is not None:
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin (B Block)")
        
        t_val = float(latest['Temp']) if 'Temp' in latest else 0.0
        if t_val > 65: st.error(f"🚨 OVERHEAT WARNING: {t_val}°C")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("Voltage", f"{latest['Voltage']:.1f} V")
        with c2: st.metric("Current", f"{latest['Current']:.2f} A")
        with c3: st.metric("Power", f"{int(latest['Power'])} W")
        with c4: st.metric("Temp", f"{t_val:.1f} °C")
        with c5:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Energy Today", f"{today_kwh:.3f} kWh")

