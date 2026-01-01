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

# Hardware Mapping
DEVICES = {
    "MAIN": "bf44d7e214c9e67fa8vhoy",
    "ESSENTIAL": "bf4c09baef731734aehesx",
    "NON_ESSENTIAL": "bff5d56df73071b658rk9b"
}

# --- 3. DATA LOADING ---
def load_data():
    try:
        cb = int(time.time() * 1000) + random.randint(1, 1000)
        # REPLACE 123456789 with the actual GID of your BEMS_Live tab
        final_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=123456789&v={cb}"
        
        df = pd.read_csv(final_url, on_bad_lines='skip', engine='python')
        
        # This line is critical: it removes hidden spaces from column names
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

def send_relay_command(dev_key, state):
    params = {"action": "control", "id": DEVICES[dev_key], "value": "true" if state else "false"}
    try:
        response = requests.get(WEB_APP_URL, params=params, timeout=60) 
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Control Error: {e}")
        return False

# --- 5. INITIAL DATA FETCH ---
df = load_data()
latest = df.iloc[-1] if not df.empty else None

# Status logic based on Main Switch
is_offline = False
try:
    # Use your Google Script's offline detection for the Main Switch
    status_check = requests.get(WEB_APP_URL, timeout=5).text
    if "OFFLINE" in status_check: is_offline = True
except: pass

# --- 6. SIDEBAR CONTROL CENTER ---
st.sidebar.title("🕹️ BEMS Control Panel")
st.sidebar.markdown("---")

def render_sidebar_switch(label, dev_key, pow_col):
    st.sidebar.subheader(label)
    p_val = float(latest[pow_col]) if latest is not None else 0.0
    
    if is_offline and dev_key == "MAIN":
        st.sidebar.error("🚨 MAIN GRID OFFLINE")
    elif p_val > 5.0:
        st.sidebar.success(f"ONLINE: {p_val} W")
    else:
        st.sidebar.warning("SHEDDED / OFF")

    c1, c2 = st.sidebar.columns(2)
    if c1.button("🟢 ON", key=f"on_{dev_key}", use_container_width=True):
        if send_relay_command(dev_key, True):
            time.sleep(40)
            st.rerun()
    if c2.button("🔴 OFF", key=f"off_{dev_key}", use_container_width=True):
        if send_relay_command(dev_key, False):
            time.sleep(25)
            st.rerun()
    st.sidebar.markdown("---")

if latest is not None:
    render_sidebar_switch("Main Building", "MAIN", "M_Pow")
    render_sidebar_switch("Essential (Lights)", "ESSENTIAL", "E_Pow")
    render_sidebar_switch("Non-Essential (AC)", "NON_ESSENTIAL", "NE_Pow")

# --- 7. MAIN DASHBOARD UI ---
if latest is not None:
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Triple-Node Digital Twin")
        
        # PRIMARY METRICS (MAIN SWITCH)
        st.markdown("### 🏛️ Main Building Overview")
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Voltage", f"{latest['M_Volt'] if not is_offline else 0:.1f} V")
            st.button("Analyze M_V", on_click=go_to_page, args=('Detail', 'M_Volt'))
        with m2:
            st.metric("Current", f"{latest['M_Curr'] if not is_offline else 0:.2f} A")
            st.button("Analyze M_I", on_click=go_to_page, args=('Detail', 'M_Curr'))
        with m3:
            st.metric("Power", f"{int(latest['M_Pow']) if not is_offline else 0} W")
            st.button("Analyze M_P", on_click=go_to_page, args=('Detail', 'M_Pow'))
        with m4:
            st.metric("Switch Temp", f"{latest['M_Temp']:.1f} °C")
            st.button("Analyze M_T", on_click=go_to_page, args=('Detail', 'M_Temp'))
        with m5:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['M_kWh'].sum()
            st.metric("Main Energy", f"{today_kwh:.3f} kWh")
            st.button("Analyze M_E", on_click=go_to_page, args=('Detail', 'M_kWh'))

        # SUB-METERING OVERVIEW
        st.markdown("---")
        st.markdown("### 🔌 Sub-Circuit Load Distribution")
        s1, s2 = st.columns(2)
        with s1:
            st.subheader("Essential (Lights/Fans)")
            st.metric("Current Load", f"{latest['E_Pow']} W")
            st.button("Analyze Essential Power", on_click=go_to_page, args=('Detail', 'E_Pow'))
        with s2:
            st.subheader("Non-Essential (AC Units)")
            st.metric("Current Load", f"{latest['NE_Pow']} W")
            st.button("Analyze Non-Essential Power", on_click=go_to_page, args=('Detail', 'NE_Pow'))

        # HOURLY POWER COMPARISON
        st.markdown("### 📊 Power Consumption Comparison (Watts)")
        today_df = df[df['Timestamp'].dt.date == datetime.now().date()].copy()
        if not today_df.empty:
            h_m = today_df.resample('H', on='Timestamp')['M_Pow'].mean().reset_index()
            h_e = today_df.resample('H', on='Timestamp')['E_Pow'].mean().reset_index()
            h_ne = today_df.resample('H', on='Timestamp')['NE_Pow'].mean().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=h_m['Timestamp'], y=h_m['M_Pow'], name='Main', marker_color='#FFAA00'))
            fig.add_trace(go.Bar(x=h_e['Timestamp'], y=h_e['E_Pow'], name='Essential', marker_color='#00FF00'))
            fig.add_trace(go.Bar(x=h_ne['Timestamp'], y=h_ne['NE_Pow'], name='Non-Essential', marker_color='#FF4B4B'))
            
            fig.update_layout(template="plotly_dark", barmode='group', dragmode=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- DETAIL PAGE ---
    else:
        target = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        st.header(f"📊 {target} Historical Analysis")

        selected_date = st.date_input("Select Date", value=datetime.now().date())
        day_df = df[df['Timestamp'].dt.date == selected_date].copy()

        if not day_df.empty:
            if "kWh" in target:
                total_usage = day_df[target].sum()
                st.metric("Total Daily Consumption", f"{total_usage:.4f} kWh")
                
                # Show hourly distribution for this specific circuit
                pow_col = target.replace("kWh", "Pow") 
                h_p = day_df.resample('H', on='Timestamp')[pow_col].mean().reset_index()
                f_h = go.Figure(go.Bar(x=h_p['Timestamp'], y=h_p[pow_col], marker_color='#00FF00'))
                f_h.update_layout(template="plotly_dark", xaxis_title="Hour", yaxis_title="Power (W)")
                st.plotly_chart(f_h, use_container_width=True)
            else:
                s1, s2 = st.columns(2)
                s1.metric("Maximum", f"{day_df[target].max():.2f}")
                if "Volt" in target or "Curr" in target:
                    active_min = day_df[day_df[target] > 0.1][target].min()
                    s2.metric("Min (Active)", f"{active_min if pd.notnull(active_min) else 0:.2f}")
                else:
                    s2.metric("Average", f"{day_df[target].mean():.2f}")

                fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target], mode='lines', fill='tozeroy', line=dict(color='#00FF00')))
                fig.update_layout(template="plotly_dark", xaxis_title="Time", yaxis_title=target)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No data available for {selected_date}")

