import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & REFRESH (60 Seconds)
st.set_page_config(page_title="BEMS Digital Twin", layout="wide")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" # Ensure this ends in output=csv

@st.cache_data(ttl=30)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

# Initialize Session State
if 'page' not in st.session_state:
    st.session_state.page = 'Home'
if 'selected_param' not in st.session_state:
    st.session_state.selected_param = None

def go_to_page(page_name, param=None):
    st.session_state.page = page_name
    st.session_state.selected_param = param

# --- DATA LOADING ---
try:
    df = load_data()
    latest = df.iloc[-1]
    
    # PARAMETER EXTRACTION
    v_actual = float(latest['Voltage'])
    i_actual = float(latest['Current'])
    p_actual = float(latest['Power'])
    
    # 2. SAFETY LOGIC
    is_fault = False
    fault_msg = []
    
    if v_actual > 258:
        is_fault = True
        fault_msg.append(f"⚠️ OVERVOLTAGE DETECTED: {v_actual}V (Limit: 258V)")
    elif v_actual < 170:
        is_fault = True
        fault_msg.append(f"⚠️ UNDERVOLTAGE DETECTED: {v_actual}V (Limit: 170V)")
        
    if i_actual > 40:
        is_fault = True
        fault_msg.append(f"⚠️ OVERCURRENT DETECTED: {i_actual}A (Limit: 40A)")

    # --- LAYER 1: THE HOME DASHBOARD ---
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin: Overview")
        
        # System Health Status
        if is_fault:
            for msg in fault_msg:
                st.error(msg)
        else:
            st.success("✅ System Operating within Normal Parameters")

        st.info(f"Last Sync: {latest['Timestamp'].strftime('%H:%M:%S')}")
        
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.metric("Voltage", f"{v_actual} V", delta=f"{v_actual-240:.1f} V (Ref: 240V)")
            st.button("Analyze Voltage →", on_click=go_to_page, args=('Detail', 'Voltage'))

        with c2:
            st.metric("Current", f"{i_actual} A", delta=None if i_actual <= 40 else "OVER LIMIT", delta_color="inverse")
            st.button("Analyze Current →", on_click=go_to_page, args=('Detail', 'Current'))

        with c3:
            st.metric("Active Power", f"{p_actual} W")
            st.button("Analyze Power →", on_click=go_to_page, args=('Detail', 'Power'))

        with c4:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Today's Units", f"{today_kwh:.3f} kWh")
            st.button("Analyze Consumption →", on_click=go_to_page, args=('Detail', 'Consumption'))

    # --- LAYER 2: THE ANALYTICS LAYER ---
    else:
        param = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        
        st.title(f"📊 {param} Detailed Analytics")
        st.divider()

        if param == "Consumption":
            # FOUR GRAPHS for Consumption
            t1, t2, t3, t4 = st.tabs(["Hourly", "Daily", "Weekly", "Monthly"])
            
            with t1:
                h_df = df.resample('H', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                fig = go.Figure(go.Bar(x=h_df['Timestamp'], y=h_df['kWh_Interval'], marker_color='#3399ff'))
                fig.update_layout(title="Hourly Energy (kWh)", template="plotly_dark", xaxis_rangeslider_visible=True)
                st.plotly_chart(fig, use_container_width=True)
            with t2:
                d_df = df.resample('D', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                st.plotly_chart(go.Figure(go.Bar(x=d_df['Timestamp'], y=d_df['kWh_Interval'], marker_color='#ffaa00')).update_layout(title="Daily Energy", template="plotly_dark", xaxis_rangeslider_visible=True))
            with t3:
                w_df = df.resample('W', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                st.plotly_chart(go.Figure(go.Bar(x=w_df['Timestamp'], y=w_df['kWh_Interval'], marker_color='#00ff00')).update_layout(title="Weekly Energy", template="plotly_dark", xaxis_rangeslider_visible=True))
            with t4:
                m_df = df.resample('M', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                st.plotly_chart(go.Figure(go.Bar(x=m_df['Timestamp'], y=m_df['kWh_Interval'], marker_color='#ff3333')).update_layout(title="Monthly Energy", template="plotly_dark", xaxis_rangeslider_visible=True))

        else:
            # THREE GRAPHS for Voltage, Current, Power
            t1, t2, t3 = st.tabs(["Minute-wise (Live)", "Hourly Average", "Daily Average"])
            
            with t1:
                fig = go.Figure(go.Scatter(x=df['Timestamp'], y=df[param], line=dict(color="#00ff00"), fill='tozeroy' if param != "Voltage" else None))
                if param == "Voltage":
                    fig.add_hline(y=258, line_dash="dot", line_color="red", annotation_text="Upper Limit")
                    fig.add_hline(y=170, line_dash="dot", line_color="red", annotation_text="Lower Limit")
                fig.update_layout(title=f"Live {param} Pulse", template="plotly_dark", xaxis_rangeslider_visible=True)
                st.plotly_chart(fig, use_container_width=True)
            with t2:
                h_df = df.resample('H', on='Timestamp').agg({param:'mean'}).reset_index()
                st.plotly_chart(go.Figure(go.Scatter(x=h_df['Timestamp'], y=h_df[param], line=dict(color="#3399ff"))).update_layout(title=f"Hourly Mean {param}", template="plotly_dark", xaxis_rangeslider_visible=True))
            with t3:
                d_df = df.resample('D', on='Timestamp').agg({param:'mean'}).reset_index()
                st.plotly_chart(go.Figure(go.Scatter(x=d_df['Timestamp'], y=d_df[param], line=dict(color="#ffaa00"))).update_layout(title=f"Daily Mean {param}", template="plotly_dark", xaxis_rangeslider_visible=True))

except Exception as e:
    st.error("System Synchronizing...")
    st.info(f"Technical Log: {e}")
