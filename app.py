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
st_autorefresh(interval=5 * 1000, key="bems_heartbeat")

# --- 2. SECRETS & URLs ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
RELAY_ID = "bf44d7e214c9e67fa8vhoy" 
SHEET_ID = "1RSHAh23D4NPwNEU9cD5JbsMsYeZVYVTUfG64_4r-zsU"

# --- 3. DATA LOADING ---
def load_data():
    try:
        cb = int(time.time() * 1000) + random.randint(1, 1000)
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
        response = requests.get(WEB_APP_URL, params=params, timeout=60) 
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Control Error: {e}")
        return False

# --- 5. INITIAL DATA FETCH & OFFLINE CHECK ---
df = load_data()
latest = df.iloc[-1] if not df.empty else None

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

if is_offline:
    st.sidebar.error("🚨 POWER OUTAGE DETECTED")
    st.sidebar.markdown("**Hardware is Offline.** Showing last known switch state.")
elif is_active:
    st.sidebar.success("✅ GRID STATUS: ACTIVE")
    st.sidebar.write(f"Current Load: {current_p} W")
else:
    st.sidebar.warning("⚡ GRID STATUS: SHEDDED")
    st.sidebar.write("AC Units are Powered OFF")

st.sidebar.markdown("---")
st.sidebar.subheader("Manual Load Control")
col_on, col_off = st.sidebar.columns(2)

if col_on.button("🟢 RESTORE", use_container_width=True):
    with st.spinner("Restoring Power..."):
        if send_relay_command(True):
            time.sleep(40)
            st.rerun()

if col_off.button("🔴 SHED", use_container_width=True):
    with st.spinner("Shedding Load..."):
        if send_relay_command(False):
            time.sleep(25) 
            st.rerun()

# --- 7. MAIN DASHBOARD UI ---
if latest is not None:
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin - B Block")
        
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
            # Temp logic: Show last known even during outage
            st.metric("Switch Temp", f"{latest['Temp']:.1f} °C")
            st.caption("Internal Hardware Temp")
            st.button("Analyze T", on_click=go_to_page, args=('Detail', 'Temp'))
        with m5:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Usage (Today)", f"{today_kwh:.3f} kWh")
            st.button("Analyze E", on_click=go_to_page, args=('Detail', 'kWh_Interval'))

        # MAIN PAGE: Hourly Power Consumption in Watts
        st.markdown("### 📊 Hourly Power Consumption (Watts)")
        today_df = df[df['Timestamp'].dt.date == datetime.now().date()].copy()
        if not today_df.empty:
            hourly_avg_p = today_df.resample('H', on='Timestamp')['Power'].mean().reset_index()
            fig = go.Figure(go.Bar(x=hourly_avg_p['Timestamp'], y=hourly_avg_p['Power'], marker_color='#FFAA00'))
            fig.update_xaxes(fixedrange=True, title="Hour")
            fig.update_yaxes(fixedrange=True, title="Power (W)")
            fig.update_layout(template="plotly_dark", dragmode=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- DETAIL PAGE ---
    else:
        target = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        st.header(f"📊 {target} Historical Analysis")

        selected_date = st.date_input("Select Date", value=datetime.now().date())
        day_df = df[df['Timestamp'].dt.date == selected_date].copy()

        if not day_df.empty:
            if target == "kWh_Interval":
                total_usage = day_df['kWh_Interval'].sum()
                st.metric("Total Daily Consumption", f"{total_usage:.4f} kWh")
                
                # Double Bar Graph for Energy
                tab1, tab2 = st.tabs(["Hourly (Watts)", "Daily Total (kWh)"])
                with tab1:
                    h_p = day_df.resample('H', on='Timestamp')['Power'].mean().reset_index()
                    f_h = go.Figure(go.Bar(x=h_p['Timestamp'], y=h_p['Power'], marker_color='#00FF00'))
                    f_h.update_layout(template="plotly_dark", xaxis_title="Hour", yaxis_title="Average Power (W)")
                    st.plotly_chart(f_h, use_container_width=True)
                with tab2:
                    d_usage = pd.DataFrame({'Metric': ['Total Daily'], 'Value': [total_usage]})
                    f_d = go.Figure(go.Bar(x=d_usage['Metric'], y=d_usage['Value'], marker_color='#00CCFF'))
                    f_d.update_layout(template="plotly_dark", yaxis_title="Energy (kWh)")
                    st.plotly_chart(f_d, use_container_width=True)
            else:
                s1, s2 = st.columns(2)
                s1.metric("Maximum", f"{day_df[target].max():.2f}")
                if target in ["Voltage", "Current"]:
                    active_min = day_df[day_df[target] > 0.1][target].min()
                    s2.metric("Min (Active)", f"{active_min if pd.notnull(active_min) else 0:.2f}")
                else:
                    s2.metric("Average", f"{day_df[target].mean():.2f}")

                fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target], mode='lines', fill='tozeroy', line=dict(color='#00FF00')))
                fig.update_layout(template="plotly_dark", xaxis_title="Time", yaxis_title=target)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No data available for {selected_date}")

