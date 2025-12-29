import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. PAGE CONFIG
st.set_page_config(page_title="BEMS Digital Twin", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=15)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

# State Management
if 'page' not in st.session_state: st.session_state.page = 'Home'
if 'selected_param' not in st.session_state: st.session_state.selected_param = None

def go_to_page(p, param=None):
    st.session_state.page = p
    st.session_state.selected_param = param

# --- DATA PROCESSING ---
try:
    df = load_data()
    latest = df.iloc[-1]
    
    # Custom CSS for a sleeker look
    st.markdown("""
        <style>
        .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #00CC96; }
        div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
        button[kind="secondary"] { border-radius: 20px; border: 1px solid #00CC96; color: #00CC96; }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.page == 'Home':
        st.title("⚡ Building Energy Management System")
        st.subheader("Digital Twin Overview")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Grid Voltage", f"{latest['Voltage']:.1f} V", delta=f"{latest['Voltage']-240:.1f}V")
            st.button("Voltage Analysis", on_click=go_to_page, args=('Detail', 'Voltage'), use_container_width=True)
        with c2:
            st.metric("Load Current", f"{latest['Current']:.2f} A")
            st.button("Current Analysis", on_click=go_to_page, args=('Detail', 'Current'), use_container_width=True)
        with c3:
            st.metric("Active Power", f"{int(latest['Power'])} W")
            st.button("Power Analysis", on_click=go_to_page, args=('Detail', 'Power'), use_container_width=True)
        with c4:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Energy Today", f"{today_kwh:.3f} kWh")
            st.button("Consumption", on_click=go_to_page, args=('Detail', 'Consumption'), use_container_width=True)

    else:
        param = st.session_state.selected_param
        st.button("← BACK TO DASHBOARD", on_click=go_to_page, args=('Home',))
        st.title(f"📊 {param} Diagnostic Center")
        
        unit_map = {"Voltage": "V", "Current": "A", "Power": "W", "Consumption": "kWh"}
        color_map = {"Voltage": "#FF4B4B", "Current": "#636EFA", "Power": "#00CC96", "Consumption": "#FFAA00"}
        unit, color = unit_map.get(param, ""), color_map.get(param, "#00ff00")

        if param == "Consumption":
            # Bar charts are best for units (accumulation)
            t1, t2, t3, t4 = st.tabs(["Hourly Units", "Daily History", "Weekly Trend", "Monthly Overview"])
            for tab, (res, t_format) in zip([t1, t2, t3, t4], [('H', '%H:00'), ('D', '%b %d'), ('W', 'Week %V'), ('ME', '%b %Y')]):
                with tab:
                    res_df = df.resample(res, on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig = go.Figure(go.Bar(x=res_df['Timestamp'], y=res_df['kWh_Interval'], marker_color=color, marker_line_width=0))
                    fig.update_layout(template="plotly_dark", hovermode="x unified", dragmode="pan")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            # Line/Area charts are best for V, I, P (continuous parameters)
            t1, t2, t3 = st.tabs(["Live Pulse (1-Min)", "Hourly Average Trend", "Daily Stability"])
            
            for tab, res in zip([t1, t2, t3], [None, 'H', 'D']):
                with tab:
                    if res:
                        # For averages, we use a smooth line to show the "envelope"
                        plot_df = df.resample(res, on='Timestamp').agg({param:'mean'}).reset_index()
                        t_format = '%b %d, %H:%M' if res == 'H' else '%b %d'
                        mode, fill = 'lines', 'none'
                    else:
                        plot_df = df
                        t_format = '%H:%M'
                        mode, fill = 'lines', 'tozeroy'

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=plot_df['Timestamp'], y=plot_df[param],
                        mode=mode, fill=fill,
                        line=dict(color=color, width=3, shape='spline'),
                        hovertemplate = f"<b>{param}:</b> %{{y:.2f}} {unit}<extra></extra>"
                    ))

                    # Safety limits only on Voltage Detail
                    if param == "Voltage" and not res:
                        fig.add_hline(y=258, line_dash="dot", line_color="rgba(255,0,0,0.5)", annotation_text="Limit")
                        fig.add_hline(y=170, line_dash="dot", line_color="rgba(255,0,0,0.5)")

                    fig.update_layout(
                        template="plotly_dark", hovermode="x unified",
                        xaxis=dict(showgrid=False, rangeslider=dict(visible=False), 
                        rangeselector=dict(buttons=list([
                            dict(count=1, label="1h", step="hour", stepmode="backward"),
                            dict(count=24, label="1d", step="hour", stepmode="backward"),
                            dict(step="all")
                        ]), bgcolor="rgba(0,0,0,0)"))
                    )
                    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Syncing... {e}")
