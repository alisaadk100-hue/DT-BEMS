import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. SETUP
st.set_page_config(page_title="BEMS Digital Twin", layout="wide")
st_autorefresh(interval=60 * 1000, key="bems_heartbeat")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv" 

@st.cache_data(ttl=15)
def load_data():
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', engine='python')
    df.columns = [str(col).strip() for col in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

# Navigation logic
if 'page' not in st.session_state: st.session_state.page = 'Home'
if 'selected_param' not in st.session_state: st.session_state.selected_param = None

def go_to_page(p, param=None):
    st.session_state.page = p
    st.session_state.selected_param = param

try:
    df = load_data()
    latest = df.iloc[-1]
    
    if st.session_state.page == 'Home':
        st.title("⚡ BEMS Digital Twin: Overview")
        # (Metric cards remain same as previous version for layout consistency)
        st.info(f"Last Sync: {latest['Timestamp'].strftime('%H:%M:%S')}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Voltage", f"{latest['Voltage']:.1f} V", delta=f"{latest['Voltage']-240:.1f} V")
            st.button("Voltage Details →", key="v", on_click=go_to_page, args=('Detail', 'Voltage'))
        with c2:
            st.metric("Current", f"{latest['Current']:.2f} A")
            st.button("Current Details →", key="i", on_click=go_to_page, args=('Detail', 'Current'))
        with c3:
            st.metric("Power", f"{int(latest['Power'])} W")
            st.button("Power Details →", key="p", on_click=go_to_page, args=('Detail', 'Power'))
        with c4:
            today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()
            st.metric("Today's Units", f"{today_kwh:.3f} kWh")
            st.button("Consumption Details →", key="c", on_click=go_to_page, args=('Detail', 'Consumption'))

    else:
        param = st.session_state.selected_param
        st.button("← Back", on_click=go_to_page, args=('Home',))
        st.title(f"📊 {param} Diagnostic Center")
        
        # Determine Units and Colors
        unit_map = {"Voltage": "V", "Current": "A", "Power": "W", "Consumption": "kWh"}
        color_map = {"Voltage": "#FF4B4B", "Current": "#636EFA", "Power": "#00CC96", "Consumption": "#FFAA00"}
        unit = unit_map.get(param, "")
        color = color_map.get(param, "#00ff00")

        if param == "Consumption":
            tabs = st.tabs(["Hourly", "Daily", "Weekly", "Monthly"])
            resolutions = [('H', '%H:%M'), ('D', '%b %d'), ('W', 'Week %V'), ('ME', '%b %Y')]
            for tab, (res, t_format) in zip(tabs, resolutions):
                with tab:
                    res_df = df.resample(res, on='Timestamp').agg({'kWh_Interval':'sum'}).reset_index()
                    fig = go.Figure(go.Bar(
                        x=res_df['Timestamp'], y=res_df['kWh_Interval'],
                        marker_color=color,
                        hovertemplate = "<b>Time:</b> %{x|" + t_format + "}<br><b>Value:</b> %{y:.3f} " + unit + "<extra></extra>"
                    ))
                    fig.update_layout(template="plotly_dark", hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            tabs = st.tabs(["Live Pulse", "Hourly Average", "Daily Trend"])
            for tab, res in zip(tabs, [None, 'H', 'D']):
                with tab:
                    if res:
                        plot_df = df.resample(res, on='Timestamp').agg({param:'mean'}).reset_index()
                        t_format = '%b %d, %H:%M' if res == 'H' else '%b %d'
                    else:
                        plot_df = df
                        t_format = '%H:%M' # Minute-wise only shows time

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=plot_df['Timestamp'], y=plot_df[param],
                        mode='lines',
                        line=dict(color=color, width=3, shape='spline'), # Spline makes the lines curvy/smooth
                        fill='tozeroy',
                        hovertemplate = "<b>Time:</b> %{x|" + t_format + "}<br><b>Value:</b> %{y:.2f} " + unit + "<extra></extra>"
                    ))

                    # INTERNAL INTERACTIVITY (Buttons inside the graph)
                    fig.update_xaxes(
                        rangeslider_visible=False, # Removed the small rusty slider
                        rangeselector=dict(
                            buttons=list([
                                dict(count=1, label="1h", step="hour", stepmode="backward"),
                                dict(count=6, label="6h", step="hour", stepmode="backward"),
                                dict(count=1, label="1d", step="day", stepmode="backward"),
                                dict(step="all")
                            ]),
                            bgcolor="#1f1f1f", font=dict(color="white")
                        )
                    )
                    
                    fig.update_layout(
                        template="plotly_dark",
                        hovermode="x unified", # Clean vertical line on hover
                        showlegend=False,
                        margin=dict(l=0, r=0, t=40, b=0),
                        # Spikelines follow the mouse cursor
                        xaxis=dict(showspikes=True, spikemode='across', spikesnap='cursor', spikedash='dot')
                    )
                    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error("Updating System...")
