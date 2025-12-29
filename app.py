import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="BEMS Digital Twin", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=15)
def load_data():
    # We use 'header=0' to ensure Streamlit reads your Row 1 as column names
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python', header=0)
    # This removes any accidental spaces in your Google Sheet headers
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
        st.title("⚡ BEMS Digital Twin")
        
        # Check for Temp in headers
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
            # We use 'kWh_Interval' as the internal key for Consumption
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Energy", f"{today_kwh:.3f} kWh")
            st.button("Analyze E", on_click=go_to_page, args=('Detail', 'Consumption'), use_container_width=True)

    # --- LAYER 2: DETAIL ---
    else:
        param = st.session_state.selected_param
        st.button("← Back", on_click=go_to_page, args=('Home',))
        
        # Logic to map 'Consumption' button to 'kWh_Interval' column
        col_to_use = 'kWh_Interval' if param == 'Consumption' else param
        
        # Check if the column actually exists in the sheet
        if col_to_use not in df.columns:
            st.error(f"Column '{col_to_use}' not found in Google Sheet. Check your headers!")
        else:
            selected_date = st.date_input("Select Date", value=datetime.now().date())
            day_df = df[df['Timestamp'].dt.date == selected_date].copy()
            
            if day_df.empty:
                st.warning("No data for this date.")
            else:
                # Summary Stats
                s1, s2, s3 = st.columns(3)
                s1.info(f"**Max**: {day_df[col_to_use].max():.2f}")
                s2.info(f"**Avg**: {day_df[col_to_use].mean():.2f}")
                s3.info(f"**Min**: {day_df[col_to_use].min():.2f}")

                # Graphs
                fig = go.Figure()
                if param == "Consumption":
                    h_df = day_df.resample('H', on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig.add_trace(go.Bar(x=h_df['Timestamp'], y=h_df['kWh_Interval'], marker_color="#FFAA00"))
                else:
                    fig.add_trace(go.Scatter(x=day_df['Timestamp'], y=day_df[col_to_use], mode='lines', line=dict(shape='spline', width=3), fill='tozeroy'))
                
                st.plotly_chart(fig.update_layout(template="plotly_dark", title=f"{param} Analysis"), use_container_width=True)

except Exception as e:
    st.error(f"Detailed Sync Error: {e}")
