import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. PAGE CONFIG
st.set_page_config(page_title="BEMS Digital Twin", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

# PASTE YOUR CSV LINK HERE
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=15)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

# Navigation Logic
if 'page' not in st.session_state: st.session_state.page = 'Home'
if 'selected_param' not in st.session_state: st.session_state.selected_param = None

def go_to_page(p, param=None):
    st.session_state.page = p
    st.session_state.selected_param = param

# --- UI STYLING ---
st.markdown("""
    <style>
    .stDateInput>div>div>input { background-color: #1f1f1f; color: #00CC96; border: 1px solid #00CC96; border-radius: 10px; }
    div[data-testid="stMetric"] { background-color: rgba(255, 255, 255, 0.03); border-radius: 15px; padding: 20px; }
    div.stInfo { background-color: rgba(0, 204, 150, 0.1); border: 1px solid #00CC96; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

try:
    df = load_data()
    latest = df.iloc[-1]

    # --- LAYER 1: HOME OVERVIEW ---
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin: Overview")
        st.caption(f"Status: Online | Last Packet: {latest['Timestamp'].strftime('%H:%M:%S')}")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Voltage", f"{latest['Voltage']:.1f} V", delta=f"{latest['Voltage']-240:.1f}V")
            st.button("Analyze Voltage", on_click=go_to_page, args=('Detail', 'Voltage'), use_container_width=True)
        with c2:
            st.metric("Current", f"{latest['Current']:.2f} A")
            st.button("Analyze Current", on_click=go_to_page, args=('Detail', 'Current'), use_container_width=True)
        with c3:
            st.metric("Active Power", f"{int(latest['Power'])} W")
            st.button("Analyze Power", on_click=go_to_page, args=('Detail', 'Power'), use_container_width=True)
        with c4:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Today's Units", f"{today_kwh:.3f} kWh")
            st.button("Analyze Consumption", on_click=go_to_page, args=('Detail', 'Consumption'), use_container_width=True)

    # --- LAYER 2: DETAILED ANALYTICS (This is where the stats go) ---
    else:
        param = st.session_state.selected_param
        col_back, col_date = st.columns([1, 1])
        with col_back:
            st.button("← Back to Dashboard", on_click=go_to_page, args=('Home',))
        with col_date:
            selected_date = st.date_input("📅 Select Date", value=datetime.now().date())
        
        st.title(f"📊 {param} Analytics")
        
        # Filter data for the chosen date
        day_df = df[df['Timestamp'].dt.date == selected_date].copy()
        
        unit_map = {"Voltage": "V", "Current": "A", "Power": "W", "Consumption": "kWh"}
        color_map = {"Voltage": "#FF4B4B", "Current": "#636EFA", "Power": "#00CC96", "Consumption": "#FFAA00"}
        unit, color = unit_map.get(param, ""), color_map.get(param, "#00ff00")

        if day_df.empty:
            st.warning(f"No data logged for {selected_date}.")
        else:
            # --- NEW STATS SUMMARY SECTION ---
            st.markdown(f"### 📋 {selected_date.strftime('%d %b')} Snapshot")
            s1, s2, s3 = st.columns(3)
            with s1:
                st.info(f"**Peak {param}**")
                st.subheader(f"{day_df[param].max():.2f} {unit}")
            with s2:
                st.info(f"**Average {param}**")
                st.subheader(f"{day_df[param].mean():.2f} {unit}")
            with s3:
                st.info(f"**Minimum {param}**")
                st.subheader(f"{day_df[param].min():.2f} {unit}")
            
            st.divider()

            # --- GRAPHS SECTION ---
            if param == "Consumption":
                t1, t2 = st.tabs(["Hourly Units", "Daily History"])
                with t1:
                    h_df = day_df.resample('H', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig = go.Figure(go.Bar(x=h_df['Timestamp'], y=h_df['kWh_Interval'], marker_color=color))
                    fig.update_layout(template="plotly_dark", xaxis=dict(dtick=3600000, tickformat="%H:%M"), title="Hourly Consumption")
                    st.plotly_chart(fig, use_container_width=True)
                with t2:
                    all_d_df = df.resample('D', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    st.plotly_chart(go.Figure(go.Bar(x=all_d_df['Timestamp'], y=all_d_df['kWh_Interval'], marker_color="#555")))
            
            else:
                t1, t2 = st.tabs(["Minute-wise Pulse", "Hourly Peak Trend"])
                with t1:
                    fig = go.Figure(go.Scatter(x=day_df['Timestamp'], y=day_df[param], mode='lines', line=dict(color=color, width=3, shape='spline'), fill='tozeroy'))
                    # Annotation for the Peak
                    peak_val = day_df[param].max()
                    peak_time = day_df.loc[day_df[param].idxmax(), 'Timestamp']
                    fig.add_annotation(x=peak_time, y=peak_val, text=f"PEAK: {peak_val:.1f}{unit}", showarrow=True, bgcolor=color, font=dict(color="black"))
                    fig.update_layout(template="plotly_dark", hovermode="x unified", xaxis=dict(tickformat="%H:%M"))
                    st.plotly_chart(fig, use_container_width=True)
                with t2:
                    h_df = day_df.resample('H', on='Timestamp').agg({param:'max'}).reset_index()
                    fig = go.Figure(go.Scatter(x=h_df['Timestamp'], y=h_df[param], mode='lines+markers', line=dict(color=color, width=2)))
                    fig.update_layout(template="plotly_dark", xaxis=dict(dtick=3600000, tickformat="%H:%M"), title="Hourly Peak Points")
                    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Syncing... {e}")
