import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
import random
from datetime import datetime, time as dt_time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="BEMS Digital Twin - B Block", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=20 * 1000, key="bems_heartbeat")

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
if 'selected_node' not in st.session_state: st.session_state.selected_node = None
if 'selected_param' not in st.session_state: st.session_state.selected_param = None

def go_to_page(p, node=None, param=None):
    st.session_state.page = p
    st.session_state.selected_node = node
    st.session_state.selected_param = param

def send_relay_command(dev_key, state):
    params = {"action": "control", "id": DEVICES[dev_key], "value": "true" if state else "false"}
    try:
        response = requests.get(WEB_APP_URL, params=params, timeout=60)
        return response.status_code == 200
    except: return False

# --- 5. DATA FETCH ---
df_live = load_data(BEMS_LIVE_GID)
latest = df_live.iloc[-1] if not df_live.empty else None

# Pre-calculate Today's Energy for Metrics
today_df = df_live[df_live['Timestamp'].dt.date == datetime.now().date()]
m_energy = today_df['M_kWh'].sum() if not today_df.empty else 0.0
e_energy = today_df['E_kWh'].sum() if not today_df.empty else 0.0
ne_energy = today_df['NE_kWh'].sum() if not today_df.empty else 0.0

# --- 6. SIDEBAR: AUTOMATION & CONTROL (STAY THE SAME) ---
st.sidebar.title("🕹️ BEMS Smart Controller")

data_mode = st.sidebar.radio("Dashboard Mode:", ["Live BEMS", "Main Archive"])
st.sidebar.markdown("---")

st.sidebar.subheader("🛡️ Safety Automation")
p_limit = st.sidebar.slider("Main Power Limit (W)", 100, 5000, 2500)
if latest is not None and float(latest['M_Pow']) > p_limit:
    st.sidebar.error(f"🚨 LIMIT EXCEEDED: {latest['M_Pow']}W")
    if send_relay_command("NON_ESSENTIAL", False):
        st.sidebar.warning("Auto-Shedding: Non-Essential OFF")

st.sidebar.subheader("📅 Time Scheduler")
t_node = st.sidebar.selectbox("Device", ["MAIN", "ESSENTIAL", "NON_ESSENTIAL"])
t_on = st.sidebar.time_input("ON Time", value=dt_time(8, 0))
t_off = st.sidebar.time_input("OFF Time", value=dt_time(18, 0))
if st.sidebar.button("Set Schedule"):
    st.sidebar.success(f"Schedule Locked for {t_node}")

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Real-Time Power")
for label, key, pow_col in [("Main", "MAIN", "M_Pow"), ("Essential", "ESSENTIAL", "E_Pow"), ("Non-Essential", "NON_ESSENTIAL", "NE_Pow")]:
    p_val = float(latest[pow_col]) if latest is not None else 0.0
    st.sidebar.write(f"**{label}:** {int(p_val)}W")
    c1, c2 = st.sidebar.columns(2)
    if c1.button(f"ON", key=f"s_on_{key}"): send_relay_command(key, True)
    if c2.button(f"OFF", key=f"s_off_{key}"): send_relay_command(key, False)

# --- 7. HOME SCREEN LOGIC ---
if st.session_state.page == 'Home':
    if data_mode == "Live BEMS":
        st.title("⚡ BEMS Triple-Node Digital Twin")
        
        # 🟢 SECTION 1: MAIN BUILDING (All Parameters)
        st.subheader("🏛️ Main Building Entry")
        m_cols = st.columns(5)
        m_params = [("Voltage", "M_Volt", "V"), ("Current", "M_Curr", "I"), ("Power", "M_Pow", "P"), ("Temp", "M_Temp", "T"), ("Energy", "M_kWh", "E")]
        for i, (lab, col, suf) in enumerate(m_params):
            with m_cols[i]:
                # If energy, show the summed today value
                val = m_energy if "kWh" in col else (latest[col] if latest is not None else 0.0)
                st.metric(lab, f"{val:.2f}" if "kWh" in col else f"{val:.1f}")
                st.button(f"Analyze {suf}", key=f"main_{col}", on_click=go_to_page, args=('Detail', 'MAIN', col))

        st.markdown("---")
        
        # 🟢 SECTION 2: SUB NODES (Power Only + Gateway to Deep Analysis)
        s1, s2 = st.columns(2)
        with s1:
            st.subheader("💡 Essential Loads")
            st.metric("Current Power", f"{latest['E_Pow']} W")
            st.metric("Today's Energy", f"{e_energy:.3f} kWh")
            st.button("Deep Analysis: Essential", key="btn_e", on_click=go_to_page, args=('NodeDetail', 'ESSENTIAL'))
        with s2:
            st.subheader("❄️ Non-Essential Loads")
            st.metric("Current Power", f"{latest['NE_Pow']} W")
            st.metric("Today's Energy", f"{ne_energy:.3f} kWh")
            st.button("Deep Analysis: Non-Essential", key="btn_ne", on_click=go_to_page, args=('NodeDetail', 'NON_ESSENTIAL'))

        st.markdown("---")

        # 🟢 SECTION 3: DAILY ENERGY COMPARISON GRAPH
        st.subheader("📊 Today's Energy Distribution (Hourly)")
        if not today_df.empty:
            h_m = today_df.resample('H', on='Timestamp')['M_kWh'].sum().reset_index()
            h_e = today_df.resample('H', on='Timestamp')['E_kWh'].sum().reset_index()
            h_ne = today_df.resample('H', on='Timestamp')['NE_kWh'].sum().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=h_m['Timestamp'], y=h_m['M_kWh'], name='Main', marker_color='#FFAA00'))
            fig.add_trace(go.Bar(x=h_e['Timestamp'], y=h_e['E_kWh'], name='Essential', marker_color='#00FF00'))
            fig.add_trace(go.Bar(x=h_ne['Timestamp'], y=h_ne['NE_kWh'], name='Non-Essential', marker_color='#FF4B4B'))
            
            fig.update_layout(template="plotly_dark", barmode='group', dragmode=False, 
                              xaxis_title="Time", yaxis_title="Energy (kWh)", height=400)
            fig.update_xaxes(fixedrange=True)
            fig.update_yaxes(fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
    else:
        # ARCHIVE VIEW
        st.title("📂 Phase 1: Historical Archive")
        st.info("Analyzing 'Archive_Main' baseline data.")
        arch_df = load_data(ARCHIVE_GID)
        a_cols = st.columns(5)
        a_params = [("Voltage", "Voltage"), ("Current", "Current"), ("Power", "Power"), ("Temp", "Temp"), ("Energy", "kWh_Interval")]
        for i, (lab, col) in enumerate(a_params):
            with a_cols[i]:
                st.button(f"📈 Analyze {lab}", key=f"arch_{col}", on_click=go_to_page, args=('Detail', 'ARCHIVE', col))

# --- 8. NODE DETAIL PAGE (Deep Analysis for Essential/Non-Essential) ---
elif st.session_state.page == 'NodeDetail':
    node = st.session_state.selected_node
    st.button("← Back to Dashboard", on_click=go_to_page, args=('Home',))
    st.header(f"🔍 {node} Detailed Parameters")
    pre = "E" if node == "ESSENTIAL" else "NE"
    
    n_cols = st.columns(5)
    n_params = [("Voltage", f"{pre}_Volt", "V"), ("Current", f"{pre}_Curr", "I"), 
                ("Power", f"{pre}_Pow", "P"), ("Temp", f"{pre}_Temp", "T"), ("Energy", f"{pre}_kWh", "E")]
    
    for i, (lab, col, suf) in enumerate(n_params):
        with n_cols[i]:
            val = latest[col] if latest is not None else 0.0
            st.metric(lab, f"{val:.2f}")
            st.button(f"Analyze {suf}", key=f"det_{col}", on_click=go_to_page, args=('Detail', node, col))

# --- 9. GRAPH DETAIL PAGE (Historical Scatter) ---
elif st.session_state.page == 'Detail':
    target = st.session_state.selected_param
    st.button("← Back", on_click=go_to_page, args=('Home' if st.session_state.selected_node in ['MAIN', 'ARCHIVE'] else 'NodeDetail', st.session_state.selected_node))
    st.header(f"📈 Historical Analysis: {target}")
    
    curr_df = load_data(ARCHIVE_GID) if st.session_state.selected_node == "ARCHIVE" else df_live
    selected_date = st.date_input("Select Date", value=datetime.now().date())
    day_df = curr_df[curr_df['Timestamp'].dt.date == selected_date].copy()

    if not day_df.empty:
        fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target], mode='lines', fill='tozeroy', line=dict(color='#FFAA00')))
        fig.update_layout(template="plotly_dark", dragmode=False)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
