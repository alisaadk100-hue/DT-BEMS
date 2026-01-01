import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
import random
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="BEMS Digital Twin - B Block", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=25 * 1000, key="bems_heartbeat")

# --- 2. SECRETS & URLs ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
SHEET_ID = "1RSHAh23D4NPwNEU9cD5JbsMsYeZVYVTUfG64_4r-zsU"
BEMS_LIVE_GID = "853758052" # Verified triple-node data
ARCHIVE_GID = "0" # Usually '0' for the first tab

DEVICES = {
    "MAIN": "bf44d7e214c9e67fa8vhoy",
    "ESSENTIAL": "bf4c09baef731734aehesx",
    "NON_ESSENTIAL": "bff5d56df73071b658rk9b"
}

# --- 3. DATA LOADING ---
def load_data(gid):
    try:
        cb = int(time.time() * 1000)
        final_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}&v={cb}"
        df = pd.read_csv(final_url, on_bad_lines='skip', engine='python')
        df.columns = [str(col).strip() for col in df.columns]
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 4. NAVIGATION ---
if 'page' not in st.session_state: st.session_state.page = 'Home'
if 'selected_param' not in st.session_state: st.session_state.selected_param = None
if 'data_mode' not in st.session_state: st.session_state.data_mode = 'Live BEMS'

def go_to_page(p, param=None):
    st.session_state.page = p
    st.session_state.selected_param = param

# --- 5. INITIAL DATA FETCH ---
df_live = load_data(BEMS_LIVE_GID)
latest = df_live.iloc[-1] if not df_live.empty else None

# --- 6. SIDEBAR CONTROL & ARCHIVE TOGGLE ---
st.sidebar.title("🕹️ BEMS Control Panel")
st.sidebar.markdown("---")

# DATA SOURCE SELECTOR
st.sidebar.subheader("📂 Data Analysis Mode")
st.session_state.data_mode = st.sidebar.radio(
    "Select Source for Analysis:", 
    ["Live BEMS", "Main Archive"],
    help="Switch between current 3-switch data and Phase 1 historical data."
)

st.sidebar.markdown("---")

def send_relay_command(dev_key, state):
    params = {"action": "control", "id": DEVICES[dev_key], "value": "true" if state else "false"}
    try:
        response = requests.get(WEB_APP_URL, params=params, timeout=60)
        return response.status_code == 200
    except: return False

def render_sidebar_controls():
    # Only show controls if in Live Mode
    for label, key, pow_col in [("Main", "MAIN", "M_Pow"), ("Essential", "ESSENTIAL", "E_Pow"), ("Non-Essential", "NON_ESSENTIAL", "NE_Pow")]:
        st.sidebar.write(f"**{label}**")
        p_val = float(latest[pow_col]) if latest is not None else 0.0
        if p_val > 5.0: st.sidebar.success(f"{p_val} W")
        else: st.sidebar.error("OFF")
        c1, c2 = st.sidebar.columns(2)
        if c1.button("ON", key=f"on_{key}"): 
            send_relay_command(key, True); time.sleep(5); st.rerun()
        if c2.button("OFF", key=f"off_{key}"): 
            send_relay_command(key, False); time.sleep(5); st.rerun()

if st.session_state.data_mode == "Live BEMS":
    render_sidebar_controls()

# --- 7. MAIN DASHBOARD ---
if st.session_state.page == 'Home':
    st.title("⚡ BEMS Triple-Node Digital Twin")
    
    # PARAMETER MATRIX
    # We use a nested loop to create Analyze buttons for every parameter of every switch
    nodes = [("Main Building", "M"), ("Essential (Lights)", "E"), ("Non-Essential (AC)", "NE")]
    params = [("Volt", "V"), ("Curr", "I"), ("Pow", "P"), ("Temp", "T"), ("kWh", "E")]
    
    for node_label, prefix in nodes:
        st.markdown(f"#### {node_label}")
        cols = st.columns(5)
        for i, (p_label, p_suffix) in enumerate(params):
            col_name = f"{prefix}_{p_label}"
            with cols[i]:
                val = latest[col_name] if latest is not None and col_name in latest else 0.0
                st.metric(p_label, f"{val:.1f}")
                st.button(f"Analyze {p_suffix}", key=f"btn_{col_name}", on_click=go_to_page, args=('Detail', col_name))
    
    st.markdown("---")
    st.markdown("### 📊 Power Comparison (Watts)")
    # (Grouped Bar Chart Code from previous version remains here)

# --- 8. DETAIL PAGE (Archive vs Live) ---
else:
    target = st.session_state.selected_param
    st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
    
    # Load correct dataset based on sidebar toggle
    current_df = load_data(ARCHIVE_GID) if st.session_state.data_mode == "Main Archive" else df_live
    
    # If Archive mode, remap old names to target
    if st.session_state.data_mode == "Main Archive":
        name_map = {"M_Volt": "Voltage", "M_Curr": "Current", "M_Pow": "Power", "M_Temp": "Temp", "M_kWh": "kWh_Interval"}
        target = name_map.get(target, target)
        st.header(f"📂 ARCHIVE: {target} Analysis")
    else:
        st.header(f"📊 LIVE BEMS: {target} Analysis")

    selected_date = st.date_input("Select Date", value=datetime.now().date())
    day_df = current_df[current_df['Timestamp'].dt.date == selected_date].copy()

    if not day_df.empty and target in day_df.columns:
        # (Standard Analytics & Graphing Code with Mobile Fixes)
        s1, s2 = st.columns(2)
        s1.metric("Maximum", f"{day_df[target].max():.2f}")
        s2.metric("Average", f"{day_df[target].mean():.2f}")
        
        fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target], mode='lines', fill='tozeroy', line=dict(color='#FFAA00')))
        fig.update_layout(template="plotly_dark", dragmode=False)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.warning("No data found for this parameter/date combination.")
