import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & REFRESH (60 Seconds)
st.set_page_config(page_title="BEMS Digital Twin", layout="wide")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

# VERSION MARKER - If you don't see this, the code hasn't updated!
st.sidebar.write("✔️ SYSTEM VERSION 2.0 (Layered)")

# Update with your CSV link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=15)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

# Initialize Session State for Navigation
if 'page' not in st.session_state:
    st.session_state.page = 'Home'
if 'selected_param' not in st.session_state:
    st.session_state.selected_param = None

# Navigation Function
def go_to_page(page_name, param=None):
    st.session_state.page = page_name
    st.session_state.selected_param = param

# --- DATA PROCESSING ---
try:
    df = load_data()
    latest = df.iloc[-1]
    
    # Values
    v_actual = float(latest['Voltage'])
    i_actual = float(latest['Current'])
    p_actual = float(latest['Power'])

    # --- LAYER 1: OVERVIEW ---
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin: Overview")
        
        # ALARM SYSTEM
        if v_actual > 258 or v_actual < 170 or i_actual > 40:
            st.error("⚠️ SYSTEM FAULT DETECTED")
        else:
            st.success("✅ System Healthy")

        st.info(f"Last Sync: {latest['Timestamp'].strftime('%H:%M:%S')}")
        
        # Metric Grid
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.metric("Voltage", f"{v_actual} V", delta=f"{v_actual-240:.1f} V")
            st.button("Analyze Voltage →", key="btn_v", on_click=go_to_page, args=('Detail', 'Voltage'))

        with c2:
            st.metric("Current", f"{i_actual} A")
            st.button("Analyze Current →", key="btn_i", on_click=go_to_page, args=('Detail', 'Current'))

        with c3:
            st.metric("Active Power", f"{p_actual} W")
            st.button("Analyze Power →", key="btn_p", on_click=go_to_page, args=('Detail', 'Power'))

        with c4:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Today's Units", f"{today_kwh:.3f} kWh")
            st.button("Analyze Consumption →", key="btn_c", on_click=go_to_page, args=('Detail', 'Consumption'))

    # --- LAYER 2: DETAILED ANALYTICS ---
    else:
        param = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        st.title(f"📊 {param} Analytics")

        if param == "Consumption":
            t1, t2, t3, t4 = st.tabs(["Hourly", "Daily", "Weekly", "Monthly"])
            # Aggregation logic for Bar Charts
            for tab, res, name in zip([t1, t2, t3, t4], ['H', 'D', 'W', 'ME'], ["Hourly", "Daily", "Weekly", "Monthly"]):
                with tab:
                    res_df = df.resample(res, on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig = go.Figure(go.Bar(x=res_df['Timestamp'], y=res_df['kWh_Interval']))
                    fig.update_layout(title=f"{name} kWh", template="plotly_dark", xaxis_rangeslider_visible=True)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            t1, t2, t3 = st.tabs(["Minute-wise", "Hourly Average", "Daily Average"])
            with t1:
                fig = go.Figure(go.Scatter(x=df['Timestamp'], y=df[param], line=dict(color="#00ff00"), fill='tozeroy' if param != "Voltage" else None))
                if param == "Voltage":
                    fig.add_hline(y=258, line_color="red", line_dash="dash")
                    fig.add_hline(y=170, line_color="red", line_dash="dash")
                fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=True)
                st.plotly_chart(fig, use_container_width=True)
            # Add Hourly/Daily Mean scatter plots here...
            with t2:
                h_df = df.resample('H', on='Timestamp').agg({param:'mean'}).reset_index()
                st.plotly_chart(go.Figure(go.Scatter(x=h_df['Timestamp'], y=h_df[param])).update_layout(template="plotly_dark", xaxis_rangeslider_visible=True))
            with t3:
                d_df = df.resample('D', on='Timestamp').agg({param:'mean'}).reset_index()
                st.plotly_chart(go.Figure(go.Scatter(x=d_df['Timestamp'], y=d_df[param])).update_layout(template="plotly_dark", xaxis_rangeslider_visible=True))

except Exception as e:
    st.error(f"Syncing... If this persists, check CSV link. Error: {e}")
