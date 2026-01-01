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
# Refresh interval set for responsiveness
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

# --- 2. SECRETS & URLs ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
RELAY_ID = "bf44d7e214c9e67fa8vhoy" 
SHEET_ID = "1RSHAh23D4NPwNEU9cD5JbsMsYeZVYVTUfG64_4r-zsU"

# --- 3. DATA LOADING ---
def load_data():
    try:
        cb = int(time.time() * 1000) + random.randint(1, 1000)
        # Using Direct Export to bypass the lag
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
        # Long timeout for the triple-verification process
        response = requests.get(WEB_APP_URL, params=params, timeout=60) 
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Control Error: {e}")
        return False

# --- 5. INITIAL DATA FETCH & OFFLINE CHECK ---
df = load_data()
latest = df.iloc[-1] if not df.empty else None

# Check Hardware Status directly from your new Google Script logic
is_offline = False
try:
    status_check = requests.get(WEB_APP_URL, timeout=5).text
    if "OFFLINE" in status_check:
        is_offline = True
except:
    pass

current_p = float(latest['Power']) if latest is not None and not is_offline else 0.0
is_active = current_p > 5.0 and not is_offline

# --- 6. SIDEBAR CONTROL CENTER ---
st.sidebar.title("🕹️ BEMS Control Panel")
st.sidebar.markdown("---")

# LIVE STATUS INDICATOR
st.sidebar.subheader("Live System Status")
if is_offline:
    st.sidebar.error("🚨 POWER OUTAGE DETECTED")
    st.sidebar.markdown("**Hardware is Offline.** Data forced to 0.")
elif is_active:
    st.sidebar.success("✅ GRID STATUS: ACTIVE")
    st.sidebar.write(f"Current Load: {current_p} W")
else:
    st.sidebar.warning("⚡ GRID STATUS: SHEDDED")
    st.sidebar.write("Non-Essential Loads are OFF")

st.sidebar.markdown("---")

# CONTROL BUTTONS
st.sidebar.subheader("Manual Load Control")
col_on, col_off = st.sidebar.columns(2)

if col_on.button("🟢 RESTORE", use_container_width=True):
    with st.spinner("Restoring Power... (45s)"):
        if send_relay_command(True):
            time.sleep(40) 
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
            st.metric("Voltage", f"{latest['Voltage'] if not is_offline else 0:.1f} V")
            st.button("Analyze V", on_click=go_to_page, args=('Detail', 'Voltage'))
        with m2: 
            st.metric("Current", f"{latest['Current'] if not is_offline else 0:.2f} A")
            st.button("Analyze I", on_click=go_to_page, args=('Detail', 'Current'))
        with m3: 
            st.metric("Power", f"{int(latest['Power']) if not is_offline else 0} W")
            st.button("Analyze P", on_click=go_to_page, args=('Detail', 'Power'))
        with m4: 
            st.metric("Temp", f"{latest['Temp']:.1f} °C")
            st.button("Analyze T", on_click=go_to_page, args=('Detail', 'Temp'))
        with m5:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Energy (Today)", f"{today_kwh:.3f} kWh")
            st.button("Analyze E", on_click=go_to_page, args=('Detail', 'kWh_Interval'))

        # Hourly kWh Bar Chart
        st.markdown("### 📊 Daily Energy Consumption (Hourly kWh)")
        today_df = df[df['Timestamp'].dt.date == datetime.now().date()].copy()
        if not today_df.empty:
            hourly_kwh = today_df.resample('H', on='Timestamp')['kWh_Interval'].sum().reset_index()
            fig = go.Figure(go.Bar(x=hourly_kwh['Timestamp'], y=hourly_kwh['kWh_Interval'], marker_color='#FFAA00'))
            # MOBILE FIX: Disable drag to allow scrolling
            fig.update_xaxes(fixedrange=True)
            fig.update_yaxes(fixedrange=True)
            fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), dragmode=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No consumption data recorded for today yet.")

    # --- DETAIL PAGE (Historical Analysis) ---
    else:
        target = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        st.header(f"📊 Historical {target} Analysis")

        # Calendar Defaults to Today
        selected_date = st.date_input("Select Date", value=datetime.now().date())
        day_df = df[df['Timestamp'].dt.date == selected_date].copy()

        if not day_df.empty:
            s1, s2, s3 = st.columns(3)
            s1.metric("Maximum", f"{day_df[target].max():.2f}")
            
            # Electrical Metric Logic: Min Active vs Average
            if target in ["Voltage", "Current"]:
                active_min = day_df[day_df[target] > 0.1][target].min()
                s2.metric("Minimum (Active)", f"{active_min if pd.notnull(active_min) else 0:.2f}")
                st.info("Voltage and Current analysis excludes outage zeros to show grid stability.")
            else:
                s2.metric("Average", f"{day_df[target].mean():.2f}")
                s3.metric("Minimum", f"{day_df[target].min():.2f}")

            # Historical Line Graph
            fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target], mode='lines', fill='tozeroy', line=dict(color='#00FF00')))
            fig.update_xaxes(fixedrange=True) # MOBILE SCROLL FIX
            fig.update_yaxes(fixedrange=True)
            fig.update_layout(template="plotly_dark", dragmode=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning(f"No data available for {selected_date}")
else:
    st.warning("⚠️ Connecting to Digital Twin Data Stream...")
