import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
import random
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="BEMS Digital Twin - B Block", layout="wide", initial_sidebar_state="expanded")
# Use 5 seconds for the demo, increase to 30s for long-term use
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

# --- 2. SECRETS & URLs ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
RELAY_ID = "bf44d7e214c9e67fa8vhoy" 
SHEET_ID = "1RSHAh23D4NPwNEU9cD5JbsMsYeZVYVTUfG64_4r-zsU"

# --- 3. DATA LOADING (Direct Export & Cache-Buster) ---
def load_data():
    try:
        cb = int(time.time() * 1000) + random.randint(1, 1000)
        # Using Direct Export to bypass the 5-minute Google 'Publish' lag
        final_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&v={cb}"
        
        df = pd.read_csv(final_url, on_bad_lines='skip', engine='python')
        df.columns = [str(col).strip() for col in df.columns]
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 4. NAVIGATION & CONTROL ---
if 'page' not in st.session_state: st.session_state.page = 'Home'
if 'selected_param' not in st.session_state: st.session_state.selected_param = None

def go_to_page(p, param=None):
    st.session_state.page = p
    st.session_state.selected_param = param

def send_relay_command(state):
    params = {"action": "control", "id": RELAY_ID, "value": "true" if state else "false"}
    try:
        # Timeout set to 60 for the long Triple-Verification process
        response = requests.get(WEB_APP_URL, params=params, timeout=60) 
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Control Error: {e}")
        return False

# --- 5. INITIAL DATA FETCH ---
df = load_data()
latest = df.iloc[-1] if not df.empty else None
# Offline Detection: If no data for > 2 mins, assume outage
is_offline = False
if latest is not None:
    diff = (datetime.now() - latest['Timestamp']).total_seconds() / 60
    if diff > 2.0: is_offline = True

# Logic for Grid Status
current_p = float(latest['Power']) if latest is not None and not is_offline else 0.0
is_active = current_p > 5.0 and not is_offline

# --- 6. SIDEBAR CONTROL CENTER ---
st.sidebar.title("🕹️ BEMS Control Panel")
st.sidebar.markdown("---")

# LIVE STATUS INDICATOR
st.sidebar.subheader("Live System Status")
if is_offline:
    st.sidebar.warning("⚠️ STATUS: OFFLINE (No Data)")
elif is_active:
    st.sidebar.success("✅ GRID STATUS: ACTIVE")
    st.sidebar.write(f"Current Load: {current_p} W")
else:
    st.sidebar.error("🚨 GRID STATUS: SHEDDED")
    st.sidebar.write("Non-Essential Loads are OFF")

st.sidebar.markdown("---")

# CONTROL BUTTONS
st.sidebar.subheader("Manual Load Control")
col_on, col_off = st.sidebar.columns(2)

if col_on.button("🟢 RESTORE", use_container_width=True):
    with st.spinner("Stabilizing Hardware... (45s)"):
        if send_relay_command(True):
            time.sleep(40) # Allow Google Script to finish triple-logging
            st.rerun()

if col_off.button("🔴 SHED", use_container_width=True):
    with st.spinner("Shedding Load... (25s)"):
        if send_relay_command(False):
            time.sleep(25) 
            st.rerun()

# --- 7. MAIN DASHBOARD UI ---
if latest is not None:
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin (B-Block Overview)")
        
        # Metrics Row
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1: 
            st.metric("Voltage", f"{latest['Voltage']:.1f} V")
            st.button("Analyze V", on_click=go_to_page, args=('Detail', 'Voltage'))
        with m2: 
            st.metric("Current", f"{latest['Current']:.2f} A")
            st.button("Analyze I", on_click=go_to_page, args=('Detail', 'Current'))
        with m3: 
            st.metric("Power", f"{int(latest['Power'])} W")
            st.button("Analyze P", on_click=go_to_page, args=('Detail', 'Power'))
        with m4: 
            st.metric("Temp", f"{latest['Temp']:.1f} °C")
            st.button("Analyze T", on_click=go_to_page, args=('Detail', 'Temp'))
        with m5:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Energy (Today)", f"{today_kwh:.3f} kWh")
            st.button("Analyze E", on_click=go_to_page, args=('Detail', 'kWh_Interval'))

        # NEW: Daily Energy Usage Graph
        st.markdown("### 📊 Daily Energy Consumption (Hourly kWh)")
        today_df = df[df['Timestamp'].dt.date == datetime.now().date()].copy()
        if not today_df.empty:
            # Resample to hourly sums for a clean consumption view
            hourly_kwh = today_df.resample('H', on='Timestamp')['kWh_Interval'].sum().reset_index()
            fig = go.Figure(go.Bar(x=hourly_kwh['Timestamp'], y=hourly_kwh['kWh_Interval'], marker_color='#FFAA00'))
            fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20), xaxis_title="Time", yaxis_title="kWh")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No consumption data recorded for today yet.")

    # --- DETAIL PAGE (Historical Analysis) ---
    else:
        target = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        st.header(f"📊 Historical {target} Analysis")

        # Fixed Calendar Logic: Defaults to current day
        selected_date = st.date_input("Select Date", value=datetime.now().date())
        day_df = df[df['Timestamp'].dt.date == selected_date].copy()

        if not day_df.empty:
            s1, s2, s3 = st.columns(3)
            s1.info(f"**Max**: {day_df[target].max():.2f}")
            s2.info(f"**Avg**: {day_df[target].mean():.2f}")
            s3.info(f"**Min**: {day_df[target].min():.2f}")

            fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target], mode='lines', fill='tozeroy', line=dict(color='#00FF00')))
            st.plotly_chart(fig.update_layout(template="plotly_dark"), use_container_width=True)
        else:
            st.warning(f"No data available for {selected_date}")

else:
    st.warning("⚠️ Connecting to Digital Twin Data Stream...")

