import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="BEMS Digital Twin", layout="wide")

# Replace with your link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRP4yZn_0PQCRB9xZcNm9bKMv6vZhk6P9kjEFX6iuXh-71ExjMWK6uRLqnZ12BgKJDtwo8a8jYRXPAf/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=10) # Fast refresh for debugging
def load_data():
    # Load data and skip bad lines
    df = pd.read_csv(SHEET_URL, on_bad_lines='skip', skip_blank_lines=True)
    
    # CLEANING: Remove spaces from column names
    df.columns = [str(col).strip() for col in df.columns]
    
    # AUTO-DETECT TIMESTAMP: If 'Timestamp' isn't found, use the first column
    if 'Timestamp' not in df.columns:
        df = df.rename(columns={df.columns[0]: 'Timestamp'})
    
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['Timestamp']) # Remove broken rows
    
    # Ensure all numeric columns are actually numbers
    for col in ['Voltage', 'Current', 'Power', 'kWh_Interval']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

try:
    df = load_data()
    
    # 1. METRICS CALCULATION
    latest = df.iloc[-1]
    today_kwh = df[df['Timestamp'].dt.date == datetime.now().date()]['kWh_Interval'].sum()

    st.title("⚡ BEMS: Live Digital Twin")
    
    # Clean UI Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Voltage", f"{latest.get('Voltage', 0)} V")
    c2.metric("Current", f"{latest.get('Current', 0)} A")
    c3.metric("Power", f"{latest.get('Power', 0)} W")
    c4.metric("Today's Energy", f"{today_kwh:.4f} kWh")

    st.divider()

    # 2. INTERACTIVE TABS
    t1, t2, t3 = st.tabs(["🕒 Minute-wise", "📅 Hourly", "📈 Daily History"])

    with t1:
        fig1 = go.Figure(go.Scatter(x=df['Timestamp'], y=df['Power'], fill='tozeroy', name='Power'))
        fig1.update_layout(title="Live Power Pulse", xaxis_rangeslider_visible=True, template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)

    with t2:
        h_df = df.resample('H', on='Timestamp').agg({'Power':'mean', 'kWh_Interval':'sum'}).reset_index()
        fig2 = go.Figure(go.Bar(x=h_df['Timestamp'], y=h_df['kWh_Interval'], name='kWh'))
        fig2.update_layout(title="Hourly Energy", xaxis_rangeslider_visible=True, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

    with t3:
        d_df = df.resample('D', on='Timestamp').agg({'Power':'mean', 'kWh_Interval':'sum'}).reset_index()
        st.bar_chart(data=d_df, x='Timestamp', y='kWh_Interval')

except Exception as e:
    st.error("⚠️ System Syncing...")
    st.write("Checking your data structure...")
    # DEBUG BOX: This will tell us exactly what's wrong
    tmp_df = pd.read_csv(SHEET_URL, nrows=1)
    st.write("I found these columns in your sheet:", list(tmp_df.columns))
    st.info("Make sure your Google Sheet headers are in the VERY FIRST ROW.")

