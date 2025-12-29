import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. SETUP
st.set_page_config(page_title="BEMS Digital Twin", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=15)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

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
        st.title("⚡ BEMS Digital Twin: Overview")
        
        # ADDED TEMPERATURE ALERT
        temp_val = float(latest.get('Temp', 0))
        if temp_val > 70:
            st.error(f"🔥 THERMAL ALARM: Breaker Temperature at {temp_val}°C!")
        
        c1, c2, c3, c4, c5 = st.columns(5) # Added 5th column
        with c1:
            st.metric("Voltage", f"{latest['Voltage']:.1f} V")
            st.button("Voltage →", on_click=go_to_page, args=('Detail', 'Voltage'), use_container_width=True)
        with c2:
            st.metric("Current", f"{latest['Current']:.2f} A")
            st.button("Current →", on_click=go_to_page, args=('Detail', 'Current'), use_container_width=True)
        with c3:
            st.metric("Power", f"{int(latest['Power'])} W")
            st.button("Power →", on_click=go_to_page, args=('Detail', 'Power'), use_container_width=True)
        with c4:
            st.metric("Temp", f"{temp_val:.1f} °C")
            st.button("Thermal →", on_click=go_to_page, args=('Detail', 'Temp'), use_container_width=True)
        with c5:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Today", f"{today_kwh:.3f} kWh")
            st.button("Energy →", on_click=go_to_page, args=('Detail', 'Consumption'), use_container_width=True)

    # --- LAYER 2: DETAIL ---
    else:
        param = st.session_state.selected_param
        col_back, col_date = st.columns([1, 1])
        with col_back: st.button("← Back", on_click=go_to_page, args=('Home',))
        with col_date: selected_date = st.date_input("📅 Date", value=datetime.now().date())
        
        day_df = df[df['Timestamp'].dt.date == selected_date].copy()
        
        # MAPPING FIX: Link 'Consumption' to 'kWh_Interval'
        target_col = 'kWh_Interval' if param == 'Consumption' else param
        unit = "kWh" if param == 'Consumption' else ("°C" if param == 'Temp' else "") # Add logic for other units
        color = "#FFAA00" if param == 'Consumption' else "#FF4B4B"

        if day_df.empty:
            st.warning("No data found for this date.")
        else:
            # STATS BAR
            s1, s2, s3 = st.columns(3)
            s1.metric(f"Peak {param}", f"{day_df[target_col].max():.2f}")
            s2.metric(f"Avg {param}", f"{day_df[target_col].mean():.2f}")
            s3.metric(f"Min {param}", f"{day_df[target_col].min():.2f}")

            if param == "Consumption":
                t1, t2 = st.tabs(["Hourly", "Daily"])
                with t1:
                    h_df = day_df.resample('H', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    st.plotly_chart(go.Figure(go.Bar(x=h_df['Timestamp'], y=h_df['kWh_Interval'], marker_color=color)).update_layout(template="plotly_dark", title="Hourly Units"))
            else:
                t1, t2 = st.tabs(["Pulse", "Hourly Trend"])
                with t1:
                    fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[target_col], mode='lines', line=dict(color=color, shape='spline'), fill='tozeroy'))
                    st.plotly_chart(fig.update_layout(template="plotly_dark", title=f"High-Res {param}"), use_container_width=True)
                with t2:
                    h_df = day_df.resample('H', on='Timestamp').agg({target_col:'max'}).reset_index()
                    st.plotly_chart(go.Figure(go.Scatter(x=h_df['Timestamp'], y=h_df[target_col], line=dict(color=color))).update_layout(template="plotly_dark", title=f"Hourly Peak {param}"))

except Exception as e:
    st.error(f"Syncing Error: {e}")
