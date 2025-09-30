import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests

# --- Page Configuration ---
st.set_page_config(page_title="Well Data Dashboard", page_icon="💦", layout="wide")

# --- Custom CSS (from your original file) ---
# (Included to maintain the visual theme)
st.markdown("""
<style>
    .stApp { background-color: #F0F2F6; }
    .stMetric { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 10px; padding: 20px; }
</style>
""", unsafe_allow_html=True)

# --- App State and API URL ---
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxitqyaIPeA67CM7j_kvW5AlZE_w_oxQMQOB36jF9zMv5YXpkphcayKulYJ6s9kqwaM/exec"
chart_theme = "streamlit"

# --- Data Fetching Function ---
@st.cache_data
def get_full_well_history(well_no):
    """Fetches and processes the full well history from the API."""
    api_url = f"{APPS_SCRIPT_URL}?wellNo={well_no}&mode=full"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            st.error(f"API Error: {data['error']}")
            return None
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        # Create helper columns for year and month
        df['year'] = df.index.year
        df['month'] = df.index.strftime('%B')
        return df
    except Exception as e:
        st.error(f"Failed to fetch or process data: {e}")
        return None

# --- NEW: Recharge Calculation Function ---
def calculate_annual_recharge(df, sy):
    """Calculates annual recharge using the Water Table Fluctuation method."""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Define hydrological year (e.g., June of year X to May of year X+1 is hydro_year X)
    df['hydro_year'] = df.index.year.where(df.index.month >= 6, df.index.year - 1)
    
    recharge_data = []
    for year, group in df.groupby('hydro_year'):
        if len(group) < 90:  # Skip years with insufficient data
            continue
        
        # In GWL data, a smaller value means higher water level (closer to surface)
        peak_level = group['value'].min()  # Post-monsoon peak
        lowest_level = group['value'].max() # Pre-monsoon low
        
        dh = lowest_level - peak_level  # Water Table Fluctuation
        
        if dh > 0: # Only consider recharge if water level rose
            recharge = sy * dh
            avg_level = group['value'].mean()
            recharge_data.append({
                'Year': f"{year}-{year+1}",
                'Recharge (m)': recharge,
                'Avg Water Level (m)': avg_level
            })
            
    return pd.DataFrame(recharge_data)

# --- Main App Interface ---
st.title("Groundwater Data Analytics 📊")

if 'well_no' in st.session_state:
    well_no = st.session_state['well_no']
    st.header(f"Analysis for Well: {well_no}")
    
    df = get_full_well_history(well_no)
    
    if df is not None and not df.empty:
        # --- Existing Analytics Section ---
        st.subheader("Historical Water Level Analysis")
        
        # Key Stats
        latest_level = df['value'].iloc[-1]
        avg_level = df['value'].mean()
        col1, col2 = st.columns(2)
        col1.metric("Most Recent Level", f"{latest_level:.2f} m")
        col2.metric("Historical Average Level", f"{avg_level:.2f} m")
        
        # Time Series Chart
        fig_line = px.line(df, y='value', title='Historical Groundwater Level')
        fig_line.update_layout(xaxis_title='Date', yaxis_title='Water Level (m below ground)', yaxis_autorange='reversed')
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.markdown("---")

        # --- NEW: Groundwater Recharge Section ---
        st.header("Groundwater Recharge Analysis (WTF Method)")
        
        # User input for Specific Yield (Sy)
        sy_value = st.slider(
            "Select Specific Yield (Sy) for Recharge Calculation:",
            min_value=0.003,
            max_value=0.160,
            value=0.050, # A common default
            step=0.001,
            format="%.3f"
        )
        
        recharge_df = calculate_annual_recharge(df, sy_value)
        
        if not recharge_df.empty:
            colA, colB = st.columns(2)
            
            with colA:
                # Graph 1: Recharge Rate Graph
                st.subheader("Annual Recharge Rate")
                fig_recharge_bar = px.bar(
                    recharge_df,
                    x='Year',
                    y='Recharge (m)',
                    title=f"Calculated Annual Recharge (Sy={sy_value})"
                )
                fig_recharge_bar.update_layout(yaxis_title="Recharge (m)")
                st.plotly_chart(fig_recharge_bar, use_container_width=True)

            with colB:
                # Graph 2: Water Level vs. Recharge Level
                st.subheader("Water Level vs. Recharge")
                fig_comparison = go.Figure()
                
                # Add Recharge as bars
                fig_comparison.add_trace(go.Bar(
                    x=recharge_df['Year'],
                    y=recharge_df['Recharge (m)'],
                    name='Recharge',
                    marker_color='lightblue'
                ))
                
                # Add Average Water Level as a line on a secondary y-axis
                fig_comparison.add_trace(go.Scatter(
                    x=recharge_df['Year'],
                    y=recharge_df['Avg Water Level (m)'],
                    name='Avg Water Level',
                    yaxis='y2',
                    line=dict(color='red', width=3)
                ))
                
                fig_comparison.update_layout(
                    title="Annual Recharge vs. Average Water Level",
                    xaxis_title="Year",
                    yaxis=dict(title="Recharge (m)"),
                    yaxis2=dict(
                        title="Avg Water Level (m below ground)",
                        overlaying="y",
                        side="right",
                        autorange="reversed" # Invert this axis
                    ),
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
                
        else:
            st.warning("Could not calculate recharge. The dataset might not contain enough data spanning pre and post-monsoon seasons.")
            
    else:
        st.error("Could not retrieve historical data for this well.")
else:
    st.warning("Please go to the WebGIS map and select a well first.")
