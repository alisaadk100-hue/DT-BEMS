import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. PAGE SETUP
st.set_page_config(page_title="BEMS Digital Twin", layout="wide")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

st.sidebar.markdown("### 🛠️ System Control")
st.sidebar.write("✔️ **Version:** 2.1 (Polished)")
st.sidebar.write(f"**Standard:** Pakistan (240V)")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=15)
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

# --- CORE LOGIC ---
try:
    df = load_data()
    latest = df.iloc[-1]
    
    # Clean Variables
    v = float(latest['Voltage'])
    i = float(latest['Current'])
    p = float(latest['Power'])

    # --- LAYER 1: THE HOME DASHBOARD ---
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Live Digital Twin")
        
        # Smart Health Header
        if v > 258 or v < 170 or i > 40:
            st.error(f"🚨 CRITICAL ALARM: System operating outside safe thresholds!")
        elif v > 250 or v < 200:
            st.warning("⚠️ WARNING: Grid voltage instability detected.")
        else:
            st.success("✅ SYSTEM HEALTHY: All parameters within standard ranges.")

        st.markdown(f"**Last Data Sync:** `{latest['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')}`")
        
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            # Color logic for Delta
            v_color = "normal" if 170 <= v <= 258 else "inverse"
            st.metric("Voltage", f"{v:.1f} V", delta=f"{v-240:.1f} V", delta_color=v_color)
            st.button("Voltage Details →", key="btn_v", on_click=go_to_page, args=('Detail', 'Voltage'))

        with c2:
            i_color = "normal" if i <= 40 else "inverse"
            st.metric("Current", f"{i:.2f} A", delta="SAFE" if i <= 40 else "OVERLOAD", delta_color=i_color)
            st.button("Current Details →", key="btn_i", on_click=go_to_page, args=('Detail', 'Current'))

        with c3:
            st.metric("Active Power", f"{int(p)} W")
            st.button("Power Details →", key="btn_p", on_click=go_to_page, args=('Detail', 'Power'))

        with c4:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Today's Units", f"{today_kwh:.3f} kWh")
            st.button("Consumption Details →", key="btn_c", on_click=go_to_page, args=('Detail', 'Consumption'))

    # --- LAYER 2: THE ANALYTICS LAYER ---
    else:
        param = st.session_state.selected_param
        st.button("← Back to Overview", on_click=go_to_page, args=('Home',))
        st.title(f"📊 {param} Diagnostic Center")
        st.divider()

        if param == "Consumption":
            t1, t2, t3, t4 = st.tabs(["Hourly", "Daily", "Weekly", "Monthly"])
            configs = [('H', 'Hourly', '#3399ff'), ('D', 'Daily', '#ffaa00'), ('W', 'Weekly', '#00ff00'), ('ME', 'Monthly', '#ff3333')]
            
            for tab, res, label, color in zip([t1, t2, t3, t4], ['H', 'D', 'W', 'ME'], ["Hourly", "Daily", "Weekly", "Monthly"], ["#3399ff", "#ffaa00", "#00ff00", "#ff3333"]):
                with tab:
                    res_df = df.resample(res, on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig = go.Figure(go.Bar(x=res_df['Timestamp'], y=res_df['kWh_Interval'], marker_color=color))
                    fig.update_layout(title=f"Total {label} Consumption (kWh)", template="plotly_dark", xaxis_rangeslider_visible=True)
                    st.plotly_chart(fig, use_container_width=True)

        else:
            t1, t2, t3 = st.tabs(["Live Pulse", "Hourly Average", "Daily Trend"])
            
            with t1:
                fig = go.Figure(go.Scatter(x=df['Timestamp'], y=df[param], line=dict(color="#00ff00", width=3), fill='tozeroy'))
                if param == "Voltage":
                    fig.add_hline(y=258, line_color="red", line_dash="dash", annotation_text="OV Limit (258V)")
                    fig.add_hline(y=170, line_color="red", line_dash="dash", annotation_text="UV Limit (170V)")
                fig.update_layout(title=f"Real-Time {param} Acquisition", template="plotly_dark", xaxis_rangeslider_visible=True)
                st.plotly_chart(fig, use_container_width=True)
            
            with t2:
                h_df = df.resample('H', on='Timestamp').agg({param:'mean'}).reset_index()
                st.plotly_chart(go.Figure(go.Scatter(x=h_df['Timestamp'], y=h_df[param], line=dict(color="#3399ff"))).update_layout(title=f"Hourly Average {param}", template="plotly_dark", xaxis_rangeslider_visible=True))
            
            with t3:
                d_df = df.resample('D', on='Timestamp').agg({param:'mean'}).reset_index()
                st.plotly_chart(go.Figure(go.Scatter(x=d_df['Timestamp'], y=d_df[param], line=dict(color="#ffaa00"))).update_layout(title=f"Daily Mean {param}", template="plotly_dark", xaxis_rangeslider_visible=True))

except Exception as e:
    st.error("🔄 System Synchronizing...")
    st.info("The Digital Twin is currently polling data from the cloud repository.")
