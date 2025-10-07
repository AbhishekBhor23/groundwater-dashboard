import streamlit as st  
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime
import folium
from streamlit_folium import st_folium

# --- Page Configuration ---
st.set_page_config(page_title="Well Data Dashboard", page_icon="💧", layout="wide")

# --- Custom CSS for Themes ---
dark_theme_css = """
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #C9D1D9; }
    div[data-testid="metric-container"] { background-color: #1C212E; border: 1px solid #2A3142; border-radius: 10px; padding: 20px; }
</style>
"""
light_theme_css = """
<style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3 { color: #111111; }
    div[data-testid="metric-container"] { background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 10px; padding: 20px; }
</style>
"""
st.markdown(dark_theme_css if st.session_state.get("theme", "Dark") == "Dark" else light_theme_css, unsafe_allow_html=True)
chart_theme = "plotly_dark" if st.session_state.get("theme", "Dark") == "Dark" else "plotly_white"

# --- Safe API Fetch ---
@st.cache_data
def get_full_well_history(well_no):
    APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwYz0qXjiJD3k6vIuJ5eNdthQV4Tf14EyiyuT8VTE0-NWN-aoY5qZXBBzUDK2LZjGsL/exec"
    api_url = f"{APPS_SCRIPT_URL}?wellNo={well_no}&mode=full"
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200 or not response.text.strip():
            st.warning("⚠️ API returned no data or invalid response.")
            return pd.DataFrame()
        try:
            data = response.json()
        except ValueError:
            st.error("⚠️ Failed to decode API response (not JSON).")
            return pd.DataFrame()
        if "error" in data:
            st.error(data["error"])
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if df.empty:
            st.warning("⚠️ API returned empty dataset.")
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.sort_values('date').dropna(subset=['date'])
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

@st.cache_data
def load_metadata(filepath):
    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(['object']):
            df[col] = df[col].str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading metadata file: {e}")
        return None

# --- Recharge Calculation ---
def calculate_annual_recharge(df, sy=0.050):
    if df is None or df.empty:
        return pd.DataFrame()
    df_copy = df.copy().set_index('date')
    df_copy['hydro_year'] = df_copy.index.year.where(df_copy.index.month >= 6, df_copy.index.year - 1)
    recharge_data = []
    for year, group in df_copy.groupby('hydro_year'):
        if len(group) < 90:
            continue
        peak = group['value'].min()
        low = group['value'].max()
        dh = low - peak
        if dh > 0:
            recharge = sy * dh
            avg = group['value'].mean()
            recharge_data.append({'Year': f"{year}-{year+1}", 'Recharge (m)': recharge, 'Avg Water Level (m)': avg})
    return pd.DataFrame(recharge_data)

# --- File Path ---
file_path = "DWLR_MAHARASHTRA_AND_GOA.csv"
metadata_df = load_metadata(file_path)

# --- Sidebar ---
st.sidebar.title("Find a Well")
if metadata_df is not None:
    states = sorted(metadata_df['State'].dropna().unique())
    selected_state = st.sidebar.selectbox("Select State", states)
    districts = sorted(metadata_df[metadata_df['State'] == selected_state]['District'].dropna().unique())
    selected_district = st.sidebar.selectbox("Select District", districts)
    blocks = sorted(metadata_df[(metadata_df['State'] == selected_state) &
                                (metadata_df['District'] == selected_district)]['Block'].dropna().unique())
    selected_block = st.sidebar.selectbox("Select Block", blocks)
    wells = sorted(metadata_df[(metadata_df['State'] == selected_state) &
                               (metadata_df['District'] == selected_district) & 
                               (metadata_df['Block'] == selected_block)]['WellNo'].dropna().unique())
    selected_well = st.sidebar.selectbox("Select Well Number", wells)
    if st.sidebar.button("Find Well", type="primary"):
        st.session_state['well_no'] = selected_well
        st.query_params["wellNo"] = selected_well
        st.rerun()

# --- Main ---
current_well_no = st.session_state.get('well_no') or st.query_params.get("wellNo")
df = None
if current_well_no:
    with st.spinner(f"Loading data for well: {current_well_no}..."):
        df = get_full_well_history(current_well_no)
else:
    st.info("Please use the sidebar to select a well.")

# --- Dashboard ---
if df is not None and not df.empty:
    st.title(f"Dashboard for Well: {current_well_no}")
    st.markdown("---")

    df['year'], df['month'] = df['date'].dt.year, df['date'].dt.strftime('%B')

    # --- Metadata ---
    if metadata_df is not None:
        meta = metadata_df[metadata_df['WellNo'].astype(str) == str(current_well_no)]
        if not meta.empty:
            st.subheader("Well Metadata")
            row = meta.iloc[0]
            c1, c2 = st.columns([1.5, 1])
            with c1:
                lat, lon = row.get('Latitude', 0), row.get('Longitude', 0)
                if pd.notna(lat) and pd.notna(lon):
                    m = folium.Map(location=[lat, lon], zoom_start=13)
                    folium.TileLayer('CartoDB positron').add_to(m)
                    folium.TileLayer(
                        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                        attr='Esri').add_to(m)
                    folium.Marker([lat, lon], popup=f"Well No: {current_well_no}").add_to(m)
                    folium.LayerControl().add_to(m)
                    st_folium(m, use_container_width=True, height=250)
            with c2:
                st.markdown(f"**State:** {row.get('State', 'N/A')}") 
                st.markdown(f"**Block:** {row.get('Block', 'N/A')}")
                st.markdown(f"**Village:** {row.get('Village', 'N/A')}")
                st.markdown(f"**Latitude:** {row.get('Latitude', 0):.4f}")
                st.markdown(f"**Longitude:** {row.get('Longitude', 0):.4f}")
            st.markdown("---")

    # --- All-Time Stats ---
    st.subheader("All-Time Statistics")
    latest, avg, minv, maxv = df['value'].iloc[-1], df['value'].mean(), df['value'].min(), df['value'].max()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest Water Level (mbgl)", f"{latest:.2f}")
    c2.metric("Average Water Level (mbgl)", f"{avg:.2f}")
    c3.metric("Highest Recorded Level (mbgl)", f"{minv:.2f}")
    c4.metric("Lowest Recorded Level (mbgl)", f"{maxv:.2f}")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Historical Trend ---
    st.subheader("Daily Water Level Over Time")
    duration_options = ["3D", "1W", "1M", "3M", "6M", "1Y", "3Y", "Max"]
    sel = st.radio("Select Duration", duration_options, index=len(duration_options)-1, horizontal=True, label_visibility="collapsed")
    end = df['date'].max()
    display_df = df
    if sel != "Max":
        mapping = {"3D":3, "1W":7, "1M":30, "3M":90, "6M":180, "1Y":365, "3Y":1095}
        display_df = df[df['date'] >= end - pd.Timedelta(days=mapping[sel])]
    fig_line = go.Figure(go.Scatter(x=display_df['date'], y=display_df['value'], mode='lines+markers', name='Water Level'))
    fig_line.update_layout(title='Daily Water Level Over Time', template=chart_theme)
    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Daily Recharge Pattern ---
    st.subheader("Daily Recharge Pattern")
    display_df['Daily Recharge Pattern'] = avg - display_df['value']  # Daily recharge pattern
    fig_recharge_daily = go.Figure(go.Scatter(
        x=display_df['date'],
        y=display_df['Daily Recharge Pattern'],
        mode='lines+markers',
        name='Daily Recharge Pattern'
    ))
    fig_recharge_daily.update_layout(
        title="Daily Recharge Pattern",
        xaxis_title="Date",
        yaxis_title="Recharge Pattern (m)",
        template=chart_theme
    )
    st.plotly_chart(fig_recharge_daily, use_container_width=True)

    # --- Annual Recharge Rate Bar Graph ---
    st.subheader("Annual Recharge Rate")
    recharge_df = calculate_annual_recharge(df)
    if not recharge_df.empty:
        fig_recharge_annual = px.bar(recharge_df, x='Year', y='Recharge (m)', title="Annual Recharge Rate")
        fig_recharge_annual.update_layout(yaxis_title="Recharge (m)", template=chart_theme)
        st.plotly_chart(fig_recharge_annual, use_container_width=True)
    else:
        st.warning("Could not calculate annual recharge — insufficient data range.")

    # --- Periodic Analysis ---
    st.subheader("Periodic Analysis")
    cA, cB = st.columns(2)
    with cA:
        yearly = df.groupby('year')['value'].mean().reset_index()
        fig_bar = px.bar(yearly, x='year', y='value', title='Average Annual Water Level')
        fig_bar.update_layout(yaxis_title="Metres", template=chart_theme)
        st.plotly_chart(fig_bar, use_container_width=True)
    with cB:
        df['month_num'] = df['date'].dt.month
        monthly = df.groupby(['month', 'month_num'])['value'].agg(['min', 'max']).reset_index().sort_values('month_num')
        fig_range = go.Figure()
        fig_range.add_trace(go.Scatter(x=monthly['month'], y=monthly['max'], mode='lines', name='Max Level', line=dict(color='red', width=3)))
        fig_range.add_trace(go.Scatter(x=monthly['month'], y=monthly['min'], mode='lines', name='Min Level', line=dict(color='blue', width=3)))
        fig_range.update_layout(title='Monthly Water Level Range', yaxis_title="Metres", template=chart_theme)
        st.plotly_chart(fig_range, use_container_width=True)
