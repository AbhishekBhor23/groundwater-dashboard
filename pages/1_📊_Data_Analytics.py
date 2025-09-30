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

# --- Custom CSS for Themes & Mobile Compatibility ---
# (Your existing CSS is kept for theme consistency)
dark_theme_css = """
<style>
    /* Main app background */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #C9D1D9; }
    div[data-testid="metric-container"] { background-color: #1C212E; border: 1px solid #2A3142; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); }
    div[data-testid="metric-container"] > div:first-of-type { color: #A0A8B4; }
    div[role="radiogroup"] { border: 1px solid #2A3142; border-radius: 7px; }
    div[role="radiogroup"] > label { border-right: 1px solid #2A3142; }
    div[role="radiogroup"] > label:has(input:checked) { background-color: #2A3142; color: #FAFAFA; }

    /* --- Mobile Compatibility --- */
    @media (max-width: 768px) {
        h1 { font-size: 1.8rem; } h2 { font-size: 1.5rem; } h3 { font-size: 1.2rem; }
        div[data-testid="metric-container"] { padding: 10px; }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.75rem; }
        .st-emotion-cache-1b228ww { flex-direction: column; }
        div[role="radiogroup"] { flex-wrap: wrap; width: 100%; }
        div[role="radiogroup"] > label { flex-grow: 1; text-align: center; }
    }
</style>
"""

light_theme_css = """
<style>
    /* Main app background */
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3 { color: #111111; }
    div[data-testid="metric-container"] { background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1); }
    div[data-testid="metric-container"] > div:first-of-type { color: #555555; }
    div[role="radiogroup"] { border: 1px solid #DCDCDC; border-radius: 7px; }
    div[role="radiogroup"] > label { border-right: 1px solid #DCDCDC; }
    div[role="radiogroup"] > label:has(input:checked) { background-color: #EAEAEA; color: #000000; }
</style>
"""

# Common CSS for both themes
common_css = """
<style>
    div[role="radiogroup"] { display: flex; justify-content: center; overflow: hidden; width: max-content; margin: 0 auto 10px auto; }
    div[role="radiogroup"] > label { background-color: transparent; padding: 6px 16px; cursor: pointer; transition: background-color 0.3s ease; }
    div[role="radiogroup"] > label:last-child { border-right: none; }
    div[role="radiogroup"] input[type="radio"] { display: none; }
</style>
"""

# Apply selected theme from session state
st.markdown(dark_theme_css if st.session_state.get("theme", "Dark") == "Dark" else light_theme_css, unsafe_allow_html=True)
st.markdown(common_css, unsafe_allow_html=True)
chart_theme = "plotly_dark" if st.session_state.get("theme", "Dark") == "Dark" else "plotly_white"


# --- Data Fetching and Loading Functions (Cached) ---
@st.cache_data
def get_full_well_history(well_no):
    """Fetches full historical data for a given well number from the API."""
    APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwYz0qXjiJD3k6vIuJ5eNdthQV4Tf14EyiyuT8VTE0-NWN-aoY5qZXBBzUDK2LZjGsL/exec"
    api_url = f"{APPS_SCRIPT_URL}?wellNo={well_no}&mode=full"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            st.error(data["error"])
            return None
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"An error occurred while fetching data: {e}")
        return None

@st.cache_data
def load_metadata(filepath):
    """Loads metadata from a given CSV file path."""
    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.strip()
        # Clean whitespace from all object columns
        for col in df.select_dtypes(['object']):
            df[col] = df[col].str.strip()
        return df
    except Exception as e:
        st.error(f"An error occurred while loading the metadata file: {e}")
        return None

# NEW: Recharge Calculation Function
def calculate_annual_recharge(df, sy):
    """Calculates annual recharge using the Water Table Fluctuation method."""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_copy = df.copy().set_index('date')
    
    df_copy['hydro_year'] = df_copy.index.year.where(df_copy.index.month >= 6, df_copy.index.year - 1)
    
    recharge_data = []
    for year, group in df_copy.groupby('hydro_year'):
        if len(group) < 90:
            continue
        
        peak_level = group['value'].min()
        lowest_level = group['value'].max()
        dh = lowest_level - peak_level
        
        if dh > 0:
            recharge = sy * dh
            avg_level = group['value'].mean()
            recharge_data.append({
                'Year': f"{year}-{year+1}",
                'Recharge (m)': recharge,
                'Avg Water Level (m)': avg_level
            })
            
    return pd.DataFrame(recharge_data)

# --- Main App Logic ---
file_path = "DWLR_MAHARASHTRA_AND_GOA.csv"
metadata_df = load_metadata(file_path)

# --- Sidebar for Well Selection ---
st.sidebar.title("Find a Well")

if metadata_df is not None:
    states = sorted(metadata_df['State'].dropna().unique())
    selected_state = st.sidebar.selectbox("Select State", states)
    
    districts = sorted(metadata_df[metadata_df['State'] == selected_state]['District'].dropna().unique())
    selected_district = st.sidebar.selectbox("Select District", districts)
    
    blocks = sorted(metadata_df[(metadata_df['State'] == selected_state) & (metadata_df['District'] == selected_district)]['Block'].dropna().unique())
    selected_block = st.sidebar.selectbox("Select Block", blocks)
    
    wells = sorted(metadata_df[(metadata_df['State'] == selected_state) & (metadata_df['District'] == selected_district) & (metadata_df['Block'] == selected_block)]['WellNo'].dropna().unique())
    selected_well = st.sidebar.selectbox("Select Well Number", wells)

    if st.sidebar.button("Find Well", type="primary"):
        st.session_state['well_no'] = selected_well
        st.query_params["wellNo"] = selected_well
        st.rerun()

# --- URL and Session State Handling ---
current_well_no = st.session_state.get('well_no') or st.query_params.get("wellNo")

# --- Data Loading ---
df = None
if current_well_no:
    with st.spinner(f"Loading data for well: {current_well_no}..."):
        df = get_full_well_history(current_well_no)
        st.session_state['data'] = df # Store in session state for other pages
else:
    st.info("Please use the sidebar to find and select a well to view its dashboard.")

# --- Main Dashboard Display ---
if df is not None and not df.empty:
    st.title(f"Dashboard for Well: {current_well_no}")
    st.markdown("---")
    
    # --- METADATA, STATS, AND HISTORICAL GRAPHS (RESTORED) ---
    df['year'], df['month'] = df['date'].dt.year, df['date'].dt.strftime('%B')
    
    well_metadata = None
    if metadata_df is not None:
        metadata_df['WellNo'] = metadata_df['WellNo'].astype(str)
        well_metadata = metadata_df[metadata_df['WellNo'] == str(current_well_no)]

    if well_metadata is not None and not well_metadata.empty:
        st.subheader("Well Metadata")
        meta_row = well_metadata.iloc[0]
        meta_col1, meta_col2 = st.columns([1.5, 1])
        with meta_col1:
            lat, lon = meta_row.get('Latitude', 0), meta_row.get('Longitude', 0)
            if pd.notna(lat) and pd.notna(lon):
                m = folium.Map(location=[lat, lon], zoom_start=13)
                folium.TileLayer('CartoDB positron', name='Normal View').add_to(m)
                folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m)
                folium.Marker([lat, lon], popup=f"Well No: {current_well_no}").add_to(m)
                folium.LayerControl().add_to(m)
                st_folium(m, use_container_width=True, height=250)
            else:
                st.info("Location coordinates not available for map.")
        with meta_col2:
            st.markdown(f"**State:** {meta_row.get('State', 'N/A')}")
            st.markdown(f"**Block:** {meta_row.get('Block', 'N/A')}")
            st.markdown(f"**Village:** {meta_row.get('Village', 'N/A')}")
            st.markdown(f"**Latitude:** {meta_row.get('Latitude', 0):.4f}")
            st.markdown(f"**Longitude:** {meta_row.get('Longitude', 0):.4f}")
        st.markdown("---")
    
    st.subheader("All-Time Statistics")
    latest_value, avg_value, min_value, max_value = df['value'].iloc[-1], df['value'].mean(), df['value'].min(), df['value'].max()
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric(label="Latest Water Level (m)", value=f"{latest_value:.2f}")
    with col2: st.metric(label="Average Water Level (m)", value=f"{avg_value:.2f}")
    with col3: st.metric(label="Highest Recorded Level (m)", value=f"{min_value:.2f}")
    with col4: st.metric(label="Lowest Recorded Level (m)", value=f"{max_value:.2f}")
    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Historical Trend")
    duration_options = ["3D", "1W", "1M", "3M", "6M", "1Y", "3Y", "Max"]
    selected_duration = st.radio("Select Duration", options=duration_options, index=len(duration_options)-1, horizontal=True, label_visibility="collapsed", key='selected_duration_key')

    end_date = df['date'].max()
    display_df = df
    if selected_duration != "Max":
        if selected_duration == "3D": start_date = end_date - pd.Timedelta(days=3)
        elif selected_duration == "1W": start_date = end_date - pd.Timedelta(weeks=1)
        elif selected_duration == "1M": start_date = end_date - pd.DateOffset(months=1)
        elif selected_duration == "3M": start_date = end_date - pd.DateOffset(months=3)
        elif selected_duration == "6M": start_date = end_date - pd.DateOffset(months=6)
        elif selected_duration == "1Y": start_date = end_date - pd.DateOffset(years=1)
        elif selected_duration == "3Y": start_date = end_date - pd.DateOffset(years=3)
        display_df = df[df['date'] >= start_date]

    fig_line = go.Figure(go.Scatter(x=display_df['date'], y=display_df['value'], mode='lines', name='Daily Water Level'))
    fig_line.update_layout(title='Daily Water Level Over Time', template=chart_theme, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.subheader("Periodic Analysis")
    colA, colB = st.columns(2)
    with colA:
        yearly_avg = df.groupby('year')['value'].mean().reset_index()
        fig_bar = px.bar(yearly_avg, x='year', y='value', title='Average Annual Water Level')
        fig_bar.update_layout(template=chart_theme, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)
    with colB:
        df['month_num'] = df['date'].dt.month
        monthly_range = df.groupby(['month', 'month_num'])['value'].agg(['min', 'max']).reset_index().sort_values('month_num')
        fig_range = go.Figure()
        fig_range.add_trace(go.Scatter(x=monthly_range['month'], y=monthly_range['max'], mode='lines', name='Max Level'))
        fig_range.add_trace(go.Scatter(x=monthly_range['month'], y=monthly_range['min'], mode='lines', name='Min Level', fill='tonexty'))
        fig_range.update_layout(title='Monthly Water Level Range', template=chart_theme, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_range, use_container_width=True)
    st.markdown("---")
    
    # --- Groundwater Recharge Section ---
    st.header("Groundwater Recharge Analysis (WTF Method)")
    
    sy_value = st.slider(
        "Select Specific Yield (Sy) for Recharge Calculation:",
        min_value=0.003, max_value=0.160, value=0.050, step=0.001,
        format="%.3f",
        help="Specific Yield (Sy) is the ratio of water that drains from a saturated rock due to gravity. Adjust this based on local aquifer properties."
    )
    
    recharge_df = calculate_annual_recharge(df, sy_value)
    
    if not recharge_df.empty:
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("Annual Recharge Rate")
            fig_recharge_bar = px.bar(
                recharge_df, x='Year', y='Recharge (m)',
                title=f"Calculated Annual Recharge (Sy={sy_value})"
            )
            fig_recharge_bar.update_layout(yaxis_title="Recharge (m)", template=chart_theme, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_recharge_bar, use_container_width=True)

        with colB:
            st.subheader("Water Level vs. Recharge")
            fig_comparison = go.Figure()
            
            fig_comparison.add_trace(go.Bar(
                x=recharge_df['Year'], y=recharge_df['Recharge (m)'],
                name='Recharge', marker_color='lightblue'
            ))
            
            fig_comparison.add_trace(go.Scatter(
                x=recharge_df['Year'], y=recharge_df['Avg Water Level (m)'],
                name='Avg Water Level', yaxis='y2', line=dict(color='red', width=3)
            ))
            
            fig_comparison.update_layout(
                title="Annual Recharge vs. Average Water Level",
                xaxis_title="Year",
                yaxis=dict(title="Recharge (m)"),
                yaxis2=dict(
                    title="Avg Water Level (m below ground)",
                    overlaying="y", side="right", autorange="reversed"
                ),
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                template=chart_theme, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_comparison, use_container_width=True)
            
    else:
        st.warning("Could not calculate recharge. The dataset might not contain enough data spanning pre and post-monsoon seasons.")

