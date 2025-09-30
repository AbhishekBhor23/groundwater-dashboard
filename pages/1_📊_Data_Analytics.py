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

# (Your existing sidebar and URL handling code is unchanged)
st.sidebar.title("Find a Well")
# ... (sidebar code omitted for brevity) ...

# --- Data Loading ---
df = None
if 'well_no' in st.session_state:
    current_well_no = st.session_state['well_no']
    with st.spinner(f"Loading data for well: {current_well_no}..."):
        df = get_full_well_history(current_well_no)
        st.session_state['data'] = df
else:
    st.info("Please use the sidebar to find and select a well to view its dashboard.")

# --- Main Dashboard Display ---
if df is not None and not df.empty:
    st.title(f"Dashboard for Well: {current_well_no}")
    st.markdown("---")
    
    # (Your existing metadata and statistics sections are unchanged)
    # ... (metadata, stats, time series, periodic analysis sections omitted for brevity) ...
    
    # --- NEW: Groundwater Recharge Section ---
    st.markdown("---")
    st.header("Groundwater Recharge Analysis (WTF Method)")
    
    # User input for Specific Yield (Sy)
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
            # Graph 1: Recharge Rate Graph
            st.subheader("Annual Recharge Rate")
            fig_recharge_bar = px.bar(
                recharge_df, x='Year', y='Recharge (m)',
                title=f"Calculated Annual Recharge (Sy={sy_value})"
            )
            fig_recharge_bar.update_layout(yaxis_title="Recharge (m)", template=chart_theme, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_recharge_bar, use_container_width=True)

        with colB:
            # Graph 2: Water Level vs. Recharge Level
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
