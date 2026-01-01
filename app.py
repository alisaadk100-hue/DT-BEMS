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
st_autorefresh(interval=5 * 1000, key="bems_heartbeat")

# --- 2. SECRETS & URLs ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
SHEET_ID = "1RSHAh23D4NPwNEU9cD5JbsMsYeZVYVTUfG64_4r-zsU"
BEMS_LIVE_GID = "853758052" 
ARCHIVE_GID = "0" 

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

# --- 4. NAVIGATION & STATE ---
if 'page' not in st.session_state: st.session_state.page = 'Home'
if 'selected_param' not in st.session_state: st.session_state.selected_param = None

def go_to_page(p, param=None):
    st.session_state.page = p
    st.session_state.selected_param = param

def send_relay_command(dev_key, state):
    params = {"action": "control", "id": DEVICES[dev_key], "value": "true" if state else "false"}
    try:
        response = requests.get(WEB_APP_URL, params=params, timeout=60)
        return response.status_code == 200
    except: return False

# --- 5. INITIAL DATA FETCH ---
df_live = load_data(BEMS_LIVE_GID)
latest = df_live.iloc[-1] if not df_live.empty else None

# --- 6. SIDEBAR: POWER STATUS & MODE TOGGLE ---
st.sidebar.title("🕹️ BEMS Master Control")
st.sidebar.markdown("---")

# A. MODE SELECTOR
st.sidebar.subheader("📂 Operational Mode")
data_mode = st.sidebar.radio(
    "Switch Dashboard View:", 
    ["Live Dashboard", "Main Archive"],
    help="Live Mode shows the Digital Twin. Archive Mode allows forensic analysis of Phase 1 data."
)

st.sidebar.markdown("---")

# B. LIVE POWER STATUS (Always visible for safety)
st.sidebar.subheader("⚡ Real-Time Load")
for label, key, pow_col in [("Building Main", "MAIN", "M_Pow"), ("Essential", "ESSENTIAL", "E_Pow"), ("Non-Essential", "NON_ESSENTIAL", "NE_Pow")]:
    p_val = float(latest[pow_col]) if latest is not None else 0.0
    col_l, col_r = st.sidebar.columns([2,1])
    col_l.write(f"**{label}**")
    if p_val > 5.0: col_r.success(f"{int(p_val)}W")
    else: col_r.error("OFF")

st.sidebar.markdown("---")

# C. SWITCH CONTROLS
st.sidebar.subheader("Manual Overrides")
for label, key in [("Main Grid", "MAIN"), ("Lights", "ESSENTIAL"), ("AC Units", "NON_ESSENTIAL")]:
    c1, c2 = st.sidebar.columns(2)
    if c1.button(f"ON ({label})", key=f"on_{key}"):
        if send_relay_command(key, True): time.sleep(5); st.rerun()
    if c2.button(f"OFF ({label})", key=f"off_{key}"):
        if send_relay_command(key, False): time.sleep(5); st.rerun()

# --- 7. HOME SCREEN LOGIC ---
if st.session_state.page == 'Home':
    
    # --- VIEW 1: LIVE BEMS DIGITAL TWIN ---
    if data_mode == "Live Dashboard":
        st.title("⚡ BEMS Triple-Node Digital Twin")
        
        # Power Matrix for all 3 switches
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
                    st.button(f"Analyze {p_suffix}", key=f"live_{col_name}", on_click=go_to_page, args=('Detail', col_name))
        
        st.markdown("---")
        st.markdown("### 📊 Power Comparison Comparison (Watts)")
        # Bar chart code goes here...

    # --- VIEW 2: ARCHIVE ANALYTICS ---
    else:
        st.title("📂 Phase 1: Historical Data Analytics")
        st.info("Currently viewing data from 'Archive_Main'. Live Digital Twin metrics are hidden to focus on historical trends.")
        
        st.markdown("### Select a Parameter to Analyze from Archive")
        # Archive parameters use the old naming convention
        arch_cols = st.columns(5)
        with arch_cols[0]: st.button("📈 Analyze Voltage", on_click=go_to_page, args=('Detail', 'Voltage'))
        with arch_cols[1]: st.button("📈 Analyze Current", on_click=go_to_page, args=('Detail', 'Current'))
        with arch_cols[2]: st.button("📈 Analyze Power", on_click=go_to_page, args=('Detail', 'Power'))
        with arch_cols[3]: st.button("📈 Analyze Temp", on_click=go_to_page, args=('Detail', 'Temp'))
        with arch_cols[4]: st.button("📈 Analyze kWh", on_click=go_to_page, args=('Detail', 'kWh_Interval'))
        
        st.markdown("---")
        st.write("Archive data provides baseline metrics before the implementation of multi-node load shedding.")

# --- 8. DETAIL PAGE LOGIC ---
else:
    target = st.session_state.selected_param
    st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
    
    # Automatically pull from Archive if that mode is selected
    current_df = load_data(ARCHIVE_GID) if data_mode == "Main Archive" else df_live
    
    st.header(f"📊 {data_mode}: {target} Analysis")
    selected_date = st.date_input("Select Date", value=datetime.now().date())
    day_df = current_df[current_df['Timestamp'].dt.date == selected_date].copy()

    if not day_df.empty and target in day_df.columns:
        s1, s2 = st.columns(2)
        s1.metric("Maximum", f"{day_df[target].max():.2f}")
        s2.metric("Average", f"{day_df[target].mean():.2f}")
        
        fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target], mode='lines', fill='tozeroy', line=dict(color='#FFAA00')))
        fig.update_layout(template="plotly_dark", dragmode=False)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.warning("No data found for this selection. Check if the date is correct for the chosen mode.")
