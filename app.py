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

# --- UI ENHANCEMENTS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        transition: 0.3s;
    }
    div[data-testid="stMetric"]:hover { border: 1px solid #00CC96; background-color: rgba(0, 204, 150, 0.05); }
    .stButton>button { border-radius: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    </style>
""", unsafe_allow_html=True)

try:
    df = load_data()
    latest = df.iloc[-1]

    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin")
        st.caption(f"Network Status: Online | Last Packet: {latest['Timestamp'].strftime('%H:%M:%S')}")
        
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

    else:
        param = st.session_state.selected_param
        st.button("← Back to Dashboard", on_click=go_to_page, args=('Home',))
        st.title(f"📊 {param} Analytics")
        
        unit_map = {"Voltage": "V", "Current": "A", "Power": "W", "Consumption": "kWh"}
        color_map = {"Voltage": "#FF4B4B", "Current": "#636EFA", "Power": "#00CC96", "Consumption": "#FFAA00"}
        unit, color = unit_map.get(param, ""), color_map.get(param, "#00ff00")

        if param == "Consumption":
            t1, t2, t3, t4 = st.tabs(["Hourly Units", "Daily History", "Weekly Trend", "Monthly Overview"])
            for tab, (res, dt_tick) in zip([t1, t2, t3, t4], [('H', 3600000), ('D', 86400000), ('W', None), ('ME', None)]):
                with tab:
                    res_df = df.resample(res, on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig = go.Figure(go.Bar(x=res_df['Timestamp'], y=res_df['kWh_Interval'], marker_color=color))
                    fig.update_layout(template="plotly_dark", hovermode="x unified", xaxis=dict(dtick=dt_tick))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            t1, t2, t3 = st.tabs(["Live Pulse (1-Min)", "Hourly Peak Trend", "Daily Stability"])
            for tab, res in zip([t1, t2, t3], [None, 'H', 'D']):
                with tab:
                    if res:
                        # PEAK-HOLD LOGIC: Using .max() instead of .mean() for accuracy
                        plot_df = df.resample(res, on='Timestamp').agg({param:'max'}).reset_index()
                        dt_tick = 3600000 if res == 'H' else 86400000
                    else:
                        plot_df = df
                        dt_tick = None

                    fig = go.Figure()
                    # Add the main curve
                    fig.add_trace(go.Scatter(
                        x=plot_df['Timestamp'], y=plot_df[param],
                        mode='lines+markers' if res else 'lines',
                        line=dict(color=color, width=3, shape='spline'),
                        fill='tozeroy',
                        hovertemplate = f"<b>{param}:</b> %{{y:.2f}} {unit}<extra></extra>"
                    ))

                    # ADD PEAK MARKER (The Max Value Point)
                    peak_idx = plot_df[param].idxmax()
                    peak_val = plot_df[param].max()
                    peak_time = plot_df['Timestamp'][peak_idx]
                    
                    fig.add_annotation(x=peak_time, y=peak_val, text=f"PEAK: {peak_val:.1f}{unit}",
                                     showarrow=True, arrowhead=1, bgcolor=color, font=dict(color="black"))

                    fig.update_layout(
                        template="plotly_dark", 
                        hovermode="x unified",
                        xaxis=dict(
                            showgrid=False,
                            dtick=dt_tick, # Force hourly ticks
                            tickformat="%H:%M\n%b %d" if res == 'H' else "%b %d",
                            rangeselector=dict(buttons=list([
                                dict(count=6, label="6h", step="hour", stepmode="backward"),
                                dict(count=24, label="1d", step="hour", stepmode="backward"),
                                dict(step="all")
                            ]), bgcolor="rgba(0,0,0,0.5)")
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Syncing... {e}")
