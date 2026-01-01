import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests  # Added for control commands
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIG & REFRESH ---
st.set_page_config(page_title="BEMS Digital Twin", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

# --- SECRETS & URLs ---
# It is better to use st.secrets for these on GitHub, but I'll use placeholders for now
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby3BXsDHRsuGg_01KC5xGAm4ebKnMEGinmkfxtZwuMebuR87AZzgCeidgeytVoVezFvqA/exec"
RELAY_ID = "bf44d7e214c9e67fa8vhoy"

# --- DATA LOADING ---
@st.cache_data(ttl=15)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python', header=0)
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

# --- CONTROL FUNCTION ---
def send_relay_command(state):
    """Sends action=control to Google Script"""
    params = {
        "action": "control",
        "id": RELAY_ID,
        "value": "true" if state else "false"
    }
    try:
        response = requests.get(WEB_APP_URL, params=params)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Control Error: {e}")
        return False

# --- SIDEBAR CONTROL CENTER ---
st.sidebar.title("🕹️ BEMS Control")
st.sidebar.markdown("---")
st.sidebar.subheader("Non-Essential Loads")
st.sidebar.info("Controls: AC Units in B Block")

col_on, col_off = st.sidebar.columns(2)
if col_on.button("🟢 RESTORE", use_container_width=True):
    if send_relay_command(True):
        st.sidebar.success("Relay: ON")
    
if col_off.button("🔴 SHED", use_container_width=True):
    if send_relay_command(False):
        st.sidebar.warning("Relay: OFF")

st.sidebar.markdown("---")
st.sidebar.subheader("Essential Status")
st.sidebar.success("Fans & Lights: PROTECTED")

# --- APP LOGIC ---
if 'page' not in st.session_state: st.session_state.page = 'Home'
if 'selected_param' not in st.session_state: st.session_state.selected_param = None

def go_to_page(p, param=None):
    st.session_state.page = p
    st.session_state.selected_param = param

try:
    df = load_data()
    latest = df.iloc[-1]

    # --- LAYER 1: OVERVIEW ---
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin (B Block)")
        
        t_val = float(latest['Temp']) if 'Temp' in latest else 0.0
        if t_val > 65: st.error(f"🚨 OVERHEAT: {t_val}°C")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Voltage", f"{latest['Voltage']:.1f} V")
            st.button("Analyze V", on_click=go_to_page, args=('Detail', 'Voltage'), use_container_width=True)
        with c2:
            st.metric("Current", f"{latest['Current']:.2f} A")
            st.button("Analyze I", on_click=go_to_page, args=('Detail', 'Current'), use_container_width=True)
        with c3:
            st.metric("Power", f"{int(latest['Power'])} W")
            st.button("Analyze P", on_click=go_to_page, args=('Detail', 'Power'), use_container_width=True)
        with c4:
            st.metric("Temp", f"{t_val:.1f} °C")
            st.button("Analyze T", on_click=go_to_page, args=('Detail', 'Temp'), use_container_width=True)
        with c5:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Energy", f"{today_kwh:.3f} kWh")
            st.button("Analyze E", on_click=go_to_page, args=('Detail', 'Consumption'), use_container_width=True)

    # --- LAYER 2: DETAIL ---
    else:
        param = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        
        col_to_use = 'kWh_Interval' if param == 'Consumption' else param
        
        if col_to_use not in df.columns:
            st.error(f"Column '{col_to_use}' not found.")
        else:
            selected_date = st.date_input("Select Date", value=datetime.now().date())
            day_df = df[df['Timestamp'].dt.date == selected_date].copy()
            
            if day_df.empty:
                st.warning("No data for this date.")
            else:
                s1, s2, s3 = st.columns(3)
                s1.info(f"**Max**: {day_df[col_to_use].max():.2f}")
                s2.info(f"**Avg**: {day_df[col_to_use].mean():.2f}")
                s3.info(f"**Min**: {day_df[col_to_use].min():.2f}")

                fig = go.Figure()
                if param == "Consumption":
                    h_df = day_df.resample('H', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig.add_trace(go.Bar(x=h_df['Timestamp'], y=h_df['kWh_Interval'], marker_color="#FFAA00"))
                else:
                    fig.add_trace(go.Scatter(x=day_df['Timestamp'], y=day_df[col_to_use], mode='lines', line=dict(shape='spline', width=3), fill='tozeroy'))
                
                st.plotly_chart(fig.update_layout(template="plotly_dark", title=f"{param} Analysis"), use_container_width=True)

except Exception as e:
    st.error(f"Detailed Sync Error: {e}")




