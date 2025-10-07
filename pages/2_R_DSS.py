import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests
from datetime import datetime
from fpdf import FPDF
import io

# --- Page Configuration ---
st.set_page_config(page_title="Decision Support System", layout="wide")

# --- Custom CSS for Themes & Mobile Compatibility ---
dark_theme_css = """
<style>
    .stApp { background-color: #0E117; color: #FAFAFA; }
    h1, h2, h3 { color: #C9D1D9; }
    .dss-container { background-color: #1C212E; border: 1px solid #2A3142; border-radius: 10px; padding: 25px; margin-bottom: 20px; }
    .stTabs [aria-selected="true"] { background-color: #2A3142; }
    div[data-testid="metric-container"] { background-color: #1C212E; border: 1px solid #2A3142; }
    div[data-testid="metric-container"] > div:first-of-type { color: #A0A8B4; }
    /* Custom CSS for Project Water Demand input field - reduce top padding */
    .stNumberInput {
        margin-top: -15px; /* Adjust this value as needed to reduce space */
    }
    /* Custom CSS for Assessment text alignment and spacing */
    .stMarkdown h4 {
        display: flex;
        align-items: center;
        margin-top: 10px; /* Adjust this value as needed to reduce space */
        margin-bottom: 5px; /* Adjust this value as needed to reduce space */
    }
    .stMarkdown h4 span {
        line-height: 1.2; /* Ensure text aligns properly with circle */
    }


    @media (max-width: 768px) {
        h1 { font-size: 1.8rem; } h2 { font-size: 1.5rem; } h3 { font-size: 1.2rem; }
        .dss-container { padding: 15px; }
        .stTabs [data-baseweb="tab-list"] { gap: 12px; }
        .stTabs [data-baseweb="tab"] { padding: 8px; height: auto; }
        .st-emotion-cache-1b228ww { flex-direction: column; }
    }
</style>
"""

light_theme_css = """
<style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3 { color: #111111; }
    .dss-container { background-color: #F0F2F6; border: 1px solid #DDDDDD; border-radius: 10px; padding: 25px; margin-bottom: 20px; }
    .stTabs [aria-selected="true"] { background-color: #EAEAEA; }
    div[data-testid="metric-container"] { background-color: #FFFFFF; border: 1px solid #EAEAEA; }
    div[data-testid="metric-container"] > div:first-of-type { color: #555555; }
    /* Custom CSS for Project Water Demand input field - reduce top padding */
    .stNumberInput {
        margin-top: -15px; /* Adjust this value as needed to reduce space */
    }
    /* Custom CSS for Assessment text alignment and spacing */
    .stMarkdown h4 {
        display: flex;
        align-items: center;
        margin-top: 10px; /* Adjust this value as needed to reduce space */
        margin-bottom: 5px; /* Adjust this value as needed to reduce space */
    }
    .stMarkdown h4 span {
        line-height: 1.2; /* Ensure text aligns properly with circle */
    }

    @media (max-width: 768px) {
        h1 { font-size: 1.8rem; } h2 { font-size: 1.5rem; } h3 { font-size: 1.2rem; }
        .dss-container { padding: 15px; }
        .stTabs [data-baseweb="tab-list"] { gap: 12px; }
        .stTabs [data-baseweb="tab"] { padding: 8px; height: auto; }
        .st-emotion-cache-1b228ww { flex-direction: column; }
    }
</style>
"""

# Apply selected theme from session state
st.markdown(dark_theme_css if st.session_state.get("theme", "Dark") == "Dark" else light_theme_css, unsafe_allow_html=True)
chart_theme = "plotly_dark" if st.session_state.get("theme", "Dark") == "Dark" else "plotly_white"


# --- Callback for syncing sliders ---
def update_master_state(master_key, child_key):
    st.session_state[master_key] = st.session_state[child_key]


# --- Data Fetching ---
@st.cache_data
def get_full_well_history(well_no):
    APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwYz0qXjiJD3k6vIuJ5eNdthQV4Tf14EyiyuT8VTE0-NWN-aoY5qZXBBzUDK2LZjGsL/exec"
    api_url = f"{APPS_SCRIPT_URL}?wellNo={well_no}&mode=full"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        if "error" in data or not data: return None
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date').reset_index(drop=True)
        return df
    except Exception:
        return None

@st.cache_data
def get_nasa_power_et_data(lat, lon):
    try:
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=7)
        api_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        params = { "parameters": "T2M", "community": "AG", "longitude": lon, "latitude": lat,
                   "start": start_date.strftime("%Y%m%d"), "end": end_date.strftime("%Y%m%d"), "format": "JSON" }
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        if "properties" in data and "parameter" in data["properties"] and "T2M" in data["properties"]["parameter"]:
            temps = data["properties"]["parameter"]["T2M"].values()
            valid_temps = [t for t in temps if t > -999]
            if valid_temps:
                avg_temp = np.mean(valid_temps)
                estimated_et0 = max(1.0, avg_temp / 5.0) 
                return round(estimated_et0, 1)
    except Exception as e:
        print(f"NASA POWER API call failed: {e}")
        return None
    return None

# --- Core DSS Calculation Functions ---
def get_monsoon_rise(df):
    if df is None or df.empty: return 0, 0
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    last_year = df['year'].max()
    pre_monsoon_level = df[(df['year'] == last_year) & (df['month'] == 5)]['value'].mean()
    post_monsoon_level = df[(df['year'] == last_year) & (df['month'] == 11)]['value'].mean()
    if pd.isna(pre_monsoon_level) or pd.isna(post_monsoon_level):
        last_level = df['value'].iloc[-1] if not df.empty else 0
        return 0, last_level
    delta_h = pre_monsoon_level - post_monsoon_level
    return max(0, delta_h), df['value'].iloc[-1]

def calculate_decline_rate(df):
    if df is None or len(df) < 12: return None
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    last_year = df['year'].max()
    dry_season_df = df[((df['year'] == last_year - 1) & (df['month'] >= 10)) | ((df['year'] == last_year) & (df['month'] <= 5))].copy()
    if len(dry_season_df) < 2: return None
    dry_season_df['day_ordinal'] = dry_season_df['date'].apply(lambda x: x.toordinal())
    x, y = dry_season_df['day_ordinal'], dry_season_df['value']
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    return slope if slope > 0 else 0

def calculate_recharge_wtf(delta_h, area_ha, specific_yield):
    return (delta_h * area_ha * specific_yield) * 0.00001

def calculate_recharge_rif(rainfall_mm, area_ha, rfif):
    a = 0.08
    return max(0, (rfif * area_ha * (rainfall_mm - a) / 1000) * 0.00001)

def calculate_validated_recharge(recharge_wtf, recharge_rif):
    if recharge_rif == 0: return recharge_wtf
    pd_value = ((recharge_wtf - recharge_rif) / recharge_rif) * 100
    if -20 <= pd_value <= 20: return recharge_wtf
    elif pd_value < -20: return 0.8 * recharge_rif
    else: return 1.2 * recharge_rif

def calculate_annual_draft(daily_pumping_m3):
    return (daily_pumping_m3 * 365) / 1_000_000_000

def calculate_et_draft(evaporation_mm_day, transpiration_mm_day, area_ha, latest_water_level_mbgl):
    total_et_draft_m3 = 0
    area_m2 = area_ha * 10000
    if latest_water_level_mbgl <= 1.0:
        total_et_draft_m3 += (evaporation_mm_day / 1000) * area_m2 * 365
    if latest_water_level_mbgl <= 3.5:
        total_et_draft_m3 += (transpiration_mm_day / 1000) * area_m2 * 365
    return total_et_draft_m3 / 1_000_000_000

def calculate_net_groundwater_availability(annual_recharge_bcm, total_draft_bcm):
    return annual_recharge_bcm - total_draft_bcm

def calculate_stage_of_extraction(total_draft_bcm, annual_recharge_bcm):
    if annual_recharge_bcm <= 0: return 200
    return (total_draft_bcm / annual_recharge_bcm) * 100

def get_recommendation(stage):
    if stage <= 70: return "SAFE: Groundwater extraction is within sustainable limits.", "green", "Safe"
    elif 70 < stage <= 90: return "SEMI-CRITICAL: Caution is advised.", "orange", "Semi-critical"
    elif 90 < stage <= 100: return "CRITICAL: High stress on resources.", "red", "Critical"
    else: return "OVER-EXPLOITED: Extraction exceeds recharge.", "darkred", "Over-Exploited"

# --- UI Helper Functions ---
def create_gauge_chart(value, title, theme):
    font_color = "white" if theme == "plotly_dark" else "black"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={'text': title, 'font': {'size': 20, 'color': font_color}},
        number={'suffix': "%", 'font': {'size': 36, 'color': font_color}},
        gauge={'axis': {'range': [None, 120]},
               'bar': {'color': "#2A3142" if theme == "plotly_dark" else "#DDDDDD"},
               'steps': [{'range': [0, 70], 'color': 'green'}, {'range': [70, 90], 'color': 'orange'},
                         {'range': [90, 100], 'color': 'red'}, {'range': [100, 120], 'color': 'darkred'}],
               'threshold': {'line': {'color': font_color, 'width': 4}, 'thickness': 0.75, 'value': value}}))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={'color': font_color}, height=300)
    return fig

@st.cache_data
def load_metadata(filepath):
    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return None

# --- PDF Report Generation ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Decision Support System - Research Report', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_report(well_no, meta_row, hist_df, common_inputs, researcher_inputs, dss_outputs, forecast_fig):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Data Analytics for Well: {well_no}", 0, 1, 'L')
    pdf.ln(5)
    
    ts_fig = go.Figure(go.Scatter(x=hist_df['date'], y=hist_df['value'], mode='lines'))
    ts_fig.update_layout(title="Historical Water Level Trend", template="plotly_white")
    pdf.image(io.BytesIO(ts_fig.to_image(format="png")), x=10, w=190)
    
    hist_df['year'] = hist_df['date'].dt.year
    yearly_avg = hist_df.groupby('year')['value'].mean().reset_index()
    bar_fig = go.Figure(data=[go.Bar(x=yearly_avg['year'], y=yearly_avg['value'])])
    bar_fig.update_layout(title="Year-over-Year Average Water Level", template="plotly_white")
    pdf.image(io.BytesIO(bar_fig.to_image(format="png")), x=10, w=190)
    
    pdf.add_page()
    hist_df['month_name'] = hist_df['date'].dt.strftime('%B')
    hist_df['month_num'] = hist_df['date'].dt.month
    monthly_range = hist_df.groupby(['month_name', 'month_num'])['value'].agg(['min', 'max']).reset_index().sort_values('month_num')
    range_fig = go.Figure()
    range_fig.add_trace(go.Scatter(x=monthly_range['month_name'], y=monthly_range['max'], mode='lines', name='Max Level'))
    range_fig.add_trace(go.Scatter(x=monthly_range['month_name'], y=monthly_range['min'], mode='lines', name='Min Level', fill='tonexty'))
    range_fig.update_layout(title="Seasonal Water Level Range", template="plotly_white")
    pdf.image(io.BytesIO(range_fig.to_image(format="png")), x=10, w=190)
    
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, "Decision Support System Scenario Analysis Report", 0, 1, 'L')
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Scenario Inputs", 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    for key, value in {**common_inputs, **researcher_inputs}.items():
        pdf.cell(0, 8, f"  - {key.replace('_', ' ').title()}: {value}", 0, 1, 'L')
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Projected Impact", 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    for key, value in dss_outputs.items():
        pdf.cell(0, 8, f"  - {key.replace('_', ' ').title()}: {value}", 0, 1, 'L')
    pdf.ln(5)
    
    forecast_fig.update_layout(template="plotly_white")
    pdf.image(io.BytesIO(forecast_fig.to_image(format="png")), x=10, w=190)
    return pdf.output(dest='S')

# --- Main Dashboard UI ---
st.title("Decision Support System")
st.markdown("---")

# Initialize session state
policy_inputs = {'recharge_canals': 0, 'recharge_swi': 0, 'recharge_gwi': 0, 'recharge_tanks': 0,
                 'recharge_artificial': 0, 'draft_irrigation': 1_000_000, 'draft_industrial': 500_000,
                 'draft_domestic': 500_000, 'evaporation': 3.0, 'transpiration': 2.0}

# Ensure base_daily_pumping exists in session state so slider changes persist & respond
defaults = {'base_daily_pumping': 1500}
for key, value in {**policy_inputs, **defaults}.items():
    if key not in st.session_state:
        st.session_state[key] = value

if 'well_no' not in st.session_state or st.session_state['well_no'] is None:
    st.info("Please select a well from the 'Data Analytics' dashboard first to use the Decision Support System.")
else:
    current_well_no = st.session_state['well_no']
    historical_df = get_full_well_history(current_well_no)
    file_path = "DWLR_MAHARASHTRA_AND_GOA.csv"
    metadata_df = load_metadata(file_path)

    st.markdown('<div class="dss-container">', unsafe_allow_html=True)
    st.header("Common Dashboard: Scenario Inputs")
    
    lat, lon = None, None
    if metadata_df is not None:
        well_metadata = metadata_df[metadata_df['WellNo'].astype(str) == str(current_well_no)]
        if not well_metadata.empty:
            meta_row = well_metadata.iloc[0]
            lat, lon = meta_row.get('Latitude'), meta_row.get('Longitude')
            st.markdown(f"#### Metadata for Well: **{current_well_no}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("State", meta_row.get('State', 'N/A'))
            c2.metric("District", meta_row.get('District', 'N/A'))
            c3.metric("Block", meta_row.get('Block', 'N/A'))
            c4.metric("Village", meta_row.get('Village', 'N/A'))
        else:
            st.warning(f"Metadata for Well No '{current_well_no}' not found.")
    st.markdown("---")

    st.markdown("#### Core Hydrogeological Factors")
    col1, col2, col3 = st.columns(3)
    with col1:
        rainfall = st.slider("Rainfall (mm)", 0, 3000, 1200, 10)
        rfif = st.slider("Rainfall Infiltration Factor (RFIF)", 0.05, 0.3, 0.15, 0.01)
    with col2:
        pumping = st.slider("Base Daily Pumping (m³/day)", 0, 5000, st.session_state.get('base_daily_pumping', 1500), 10, key='base_daily_pumping')
        specific_yield = st.slider("Specific Yield (Sy)", 0.01, 0.30, 0.12, 0.01)
    with col3:
        area = st.slider("Assessment Area (Ha)", 10, 50000, 10000, 100)

    pumping = st.session_state.base_daily_pumping

    delta_h, latest_level = get_monsoon_rise(historical_df)
    base_recharge_wtf = calculate_recharge_wtf(delta_h, area, specific_yield)
    base_recharge_rif = calculate_recharge_rif(rainfall, area, rfif)
    base_annual_recharge = calculate_validated_recharge(base_recharge_wtf, base_recharge_rif)
    base_annual_draft = calculate_annual_draft(pumping)
    base_net_availability = calculate_net_groundwater_availability(base_annual_recharge, base_annual_draft)
    base_stage_of_extraction = calculate_stage_of_extraction(base_annual_draft, base_annual_recharge)
    
    additional_recharge_bcm = sum(st.session_state[k] for k in policy_inputs if 'recharge' in k) / 1_000_000_000
    policy_annual_draft_bcm = sum(st.session_state[k] for k in policy_inputs if 'draft' in k) / 1_000_000_000
    et_draft_bcm = calculate_et_draft(st.session_state.evaporation, st.session_state.transpiration, area, latest_level)

    final_recharge = base_annual_recharge + additional_recharge_bcm
    final_draft = base_annual_draft + policy_annual_draft_bcm + et_draft_bcm
    final_net_availability = calculate_net_groundwater_availability(final_recharge, final_draft)
    stage_after = calculate_stage_of_extraction(final_draft, final_recharge)

    st.markdown("---")
    st.markdown("#### Groundwater Level Forecast")
    st.info("This forecast is based on the combined inputs from all Core Factors and Intervention Levers.")
    if historical_df is not None and not historical_df.empty:
        if area > 0 and specific_yield > 0:
            delta_h_forecast_annual = (final_net_availability * 1_000_000_000) / ((area * 10000) * specific_yield)
            forecasted_level_main = latest_level - (delta_h_forecast_annual / 4)
        else:
            forecasted_level_main = latest_level
        last_date = historical_df['date'].iloc[-1]
        forecast_date_main = last_date + pd.DateOffset(months=3)
        fig_forecast = go.Figure()
        fig_forecast.add_trace(go.Scatter(x=historical_df['date'], y=historical_df['value'], mode='lines', name='Historical Water Level'))
        fig_forecast.add_trace(go.Scatter(x=[last_date, forecast_date_main], y=[latest_level, forecasted_level_main], mode='lines+markers', name='3-Month Forecast', line=dict(dash='dot')))
        fig_forecast.update_layout(title='Groundwater Level Forecast', template=chart_theme, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_forecast, use_container_width=True)
    else:
        st.warning("Historical data not available for this well.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    farmer_tab, researcher_tab, policymaker_tab, planners_tab = st.tabs(["For Farmers", "For Researchers", "For Policy Makers", "For Planners"])

    def render_prediction_section(user_type):
        st.markdown("---")
        st.subheader("Custom Forecast")
        duration_months = st.slider("Forecast Duration (Months)", 1, 12, 3, key=f"duration_{user_type}")
        if area > 0 and specific_yield > 0:
            delta_h_forecast_annual = (final_net_availability * 1_000_000_000) / ((area * 10000) * specific_yield)
            forecasted_level = latest_level - (delta_h_forecast_annual / 12 * duration_months)
        else:
            forecasted_level = latest_level
        
        recommendation_after, color_after, _ = get_recommendation(stage_after)
        pred_col1, pred_col2 = st.columns(2)
        with pred_col1:
            st.metric(label=f"Predicted Level after {duration_months} months", value=f"{forecasted_level:.2f} m")
            st.metric(label="Predicted Stage of Extraction", value=f"{stage_after:.2f} %")
        with pred_col2:
            st.markdown(f"**Projected Status:**")
            st.markdown(f"<p style='color:{color_after}; font-size: 18px; border: 1px solid {color_after}; padding: 10px; border-radius: 5px;'>{recommendation_after}</p>", unsafe_allow_html=True)

    def render_sustainability_assessment():
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Project Sustainability Assessment")
        # Added a key for the number input to prevent re-rendering issues
        demand_mcm = st.number_input("Project Water Demand (MCM)", min_value=0.0, value=1.0, step=0.5, key="project_demand_input")
        
        projected_net_avail_mcm = final_net_availability * 1000
        net_avail_for_future_use_mcm = projected_net_avail_mcm * 0.9975
        remaining_surplus = max(0, net_avail_for_future_use_mcm - demand_mcm)
        
        # Calculate the new stage of extraction including the project's demand
        new_draft_bcm = final_draft + (demand_mcm / 1000)
        new_stage = calculate_stage_of_extraction(new_draft_bcm, final_recharge)

        # NEW LOGIC with brighter colors, increased circle size, and reduced spacing
        circle_size = "20px" # Increased circle size
        margin_right = "4px" # Reduced margin to reduce space

        if new_stage < 70:
            status_display = f"Sustainable"
            color = "#32CD32" # LimeGreen
        elif 70 <= new_stage <= 90:
            status_display = f"Semi-critical"
            color = "#FFD700" # Gold
        elif 90 < new_stage <= 100:
            status_display = f"Critical"
            color = "#FFA500" # Orange
        else: # new_stage > 100
            status_display = f"Non-sustainable"
            color = "#FF0000" # Red
        
        # Render the Assessment with custom styling to match the image
        st.markdown(f"""
            <h4>Assessment: 
                <span style='display:inline-block; vertical-align:middle; margin-left: 8px; margin-right:{margin_right}; height:{circle_size}; width:{circle_size}; border-radius:50%; background-color:{color};'></span>
                <span>{status_display}</span>
            </h4>
        """, unsafe_allow_html=True)
        
        res_col1, res_col2 = st.columns(2)
        
        with res_col1:
            st.metric("Net Available for Future Use", f"{net_avail_for_future_use_mcm:.2f} MCM")
            st.metric("Project Demand", f"{demand_mcm:.2f} MCM")
            st.metric("Remaining Surplus", f"{remaining_surplus:.2f} MCM")

        with res_col2:
            _, _, category_before_project = get_recommendation(stage_after)
            stage_increase = new_stage - stage_after
            st.metric(f"Projected Stage Before Project", f"{stage_after:.2f}% ({category_before_project})")
            st.metric("Projected Stage After Project", f"{new_stage:.2f}%", 
                      delta=f"{stage_increase:.2f}%" if stage_increase != 0 else None, 
                      delta_color="inverse")

    with farmer_tab:
        st.markdown('<div class="dss-container">', unsafe_allow_html=True)
        st.header("Irrigation Calculator")
        CROP_COEFFICIENTS = {"Wheat": {"Initial": 0.40, "Development": 0.80, "Mid-Season": 1.15, "Late Season": 0.35},
                               "Sugarcane": {"Initial": 0.40, "Mid-Season": 1.25, "Late Season": 0.75},
                               "Cotton": {"Initial": 0.35, "Mid-Season": 1.20, "Late Season": 0.60}}
        IRRIGATION_EFFICIENCY = {"Sandy": {"Flood / Furrow": 0.60, "Sprinkler": 0.80, "Drip": 0.90},
                                   "Loam": {"Flood / Furrow": 0.75, "Sprinkler": 0.80, "Drip": 0.90},
                                   "Clay": {"Flood / Furrow": 0.75, "Sprinkler": 0.80, "Drip": 0.90}}
        farm_col1, farm_col2 = st.columns(2)
        with farm_col1:
            st.subheader("Farm & Crop Inputs")
            crop_type = st.selectbox("Crop Type", list(CROP_COEFFICIENTS.keys()))
            growth_stage = st.selectbox("Growth Stage", list(CROP_COEFFICIENTS[crop_type].keys()))
            soil_type = st.selectbox("Soil Type", ["Sandy", "Loam", "Clay"])
            irrigation_method = st.selectbox("Irrigation Method", ["Flood / Furrow", "Sprinkler", "Drip"])
            farm_area_acres = st.slider("Farm Area (acres)", 1, 25, 5)
            pump_power_hp = st.slider("Pump Power (HP)", 1, 20, 5)
        with farm_col2:
            st.subheader("Weather & Environment")
            et0_default = 5.0
            et0_caption = "Adjust based on current conditions."
            if lat and lon:
                with st.spinner("Fetching weather..."):
                    estimated_et0 = get_nasa_power_et_data(lat, lon)
                if estimated_et0:
                    et0_default = estimated_et0
                    et0_caption = "Default value from NASA POWER data."
            et0 = st.slider("Reference Evapotranspiration (ET₀ mm/day)", 1.0, 10.0, et0_default, 0.1)
            st.caption(et0_caption)
            recent_rainfall_mm = st.slider("Recent Rainfall (mm)", 0, 100, 0, 1)
            kc = CROP_COEFFICIENTS[crop_type][growth_stage]
            nir_mm = (et0 * kc) - recent_rainfall_mm
            st.markdown("---")
            st.subheader("Irrigation Recommendation")
            if nir_mm <= 0:
                st.success("No irrigation needed.")
            else:
                app_eff = IRRIGATION_EFFICIENCY[soil_type][irrigation_method]
                vol_m3 = (nir_mm * (farm_area_acres * 4047)) / (1000 * app_eff)
                total_head_m = (latest_level if latest_level > 0 else 5) + 2
                flow_rate_m3_hr = (pump_power_hp * 0.65 * 367) / total_head_m if total_head_m > 0 else 0
                pump_hours = vol_m3 / flow_rate_m3_hr if flow_rate_m3_hr > 0 else 0
                st.metric("Required Pumping Time", f"{pump_hours:.2f} hours")
        render_prediction_section("farmer")
        st.markdown('</div>', unsafe_allow_html=True)

    def render_intervention_view(user_type):
        st.markdown('<div class="dss-container">', unsafe_allow_html=True)
        header_text = "Groundwater Modeling & Analysis" if user_type == "researcher" else "Regional Water Resource Planning"
        st.header(header_text)
        st.subheader("Intervention Levers")
        policy_col1, policy_col2 = st.columns(2)
        with policy_col1:
            st.markdown("<h5>Inflow Factors</h5>", unsafe_allow_html=True)
            st.slider("Recharge from Canals (m³)", 0, 30_000_000, st.session_state.recharge_canals, 20_000, key=f'recharge_canals_{user_type}', on_change=update_master_state, args=('recharge_canals', f'recharge_canals_{user_type}'))
            st.slider("Recharge from SWI (m³)", 0, 20_000_000, st.session_state.recharge_swi, 20_000, key=f'recharge_swi_{user_type}', on_change=update_master_state, args=('recharge_swi', f'recharge_swi_{user_type}'))
            st.slider("Recharge from GWI (m³)", 0, 15_000_000, st.session_state.recharge_gwi, 20_000, key=f'recharge_gwi_{user_type}', on_change=update_master_state, args=('recharge_gwi', f'recharge_gwi_{user_type}'))
            st.slider("Recharge from Tanks (m³)", 0, 5_000_000, st.session_state.recharge_tanks, 20_000, key=f'recharge_tanks_{user_type}', on_change=update_master_state, args=('recharge_tanks', f'recharge_tanks_{user_type}'))
            st.slider("Artificial Recharge (m³)", 0, 10_000_000, st.session_state.recharge_artificial, 20_000, key=f'recharge_artificial_{user_type}', on_change=update_master_state, args=('recharge_artificial', f'recharge_artificial_{user_type}'))
        with policy_col2:
            st.markdown("<h5>Outflow Factors</h5>", unsafe_allow_html=True)
            st.slider("GW Extraction for Irrigation (m³)", 0, 20_000_000, st.session_state.draft_irrigation, 10_000, key=f'draft_irrigation_{user_type}', on_change=update_master_state, args=('draft_irrigation', f'draft_irrigation_{user_type}'))
            st.slider("GW Extraction for Industry (m³)", 0, 30_000_000, st.session_state.draft_industrial, 10_000, key=f'draft_industrial_{user_type}', on_change=update_master_state, args=('draft_industrial', f'draft_industrial_{user_type}'))
            st.slider("GW Extraction for Domestic (m³)", 0, 5_000_000, st.session_state.draft_domestic, 10_000, key=f'draft_domestic_{user_type}', on_change=update_master_state, args=('draft_domestic', f'draft_domestic_{user_type}'))
            if user_type == "researcher":
                st.markdown("<h6>Environmental Outflows</h6>", unsafe_allow_html=True)
                st.slider("Evaporation (mm/day)", 0.5, 12.0, st.session_state.evaporation, 0.1, key=f'evaporation_{user_type}', on_change=update_master_state, args=('evaporation', f'evaporation_{user_type}'))
                st.slider("Transpiration (mm/day)", 0.1, 10.0, st.session_state.transpiration, 0.1, key=f'transpiration_{user_type}', on_change=update_master_state, args=('transpiration', f'transpiration_{user_type}'))
        
        st.subheader("Projected Impact")
        display_net_availability = max(0, final_net_availability)
        impact_col1, impact_col2 = st.columns(2)
        with impact_col1:
            st.metric(label="Projected Net Availability (MCM)", value=f"{(display_net_availability * 1000):.2f}", delta=f"{((final_net_availability - base_net_availability) * 1000):.2f} MCM")
            st.metric(label="Projected Stage of Extraction (%)", value=f"{stage_after:.2f} %", delta=f"{(stage_after - base_stage_of_extraction):.2f} %", delta_color="inverse")
        with impact_col2:
            rec_text, color, _ = get_recommendation(stage_after)
            st.markdown(f"**Projected Outcome:**")
            st.markdown(f"<p style='color:{color};font-size:18px;border:1px solid {color};padding:10px;border-radius:5px;'>{rec_text}</p>", unsafe_allow_html=True)
        
        render_prediction_section(user_type)
        
        if user_type == "researcher":
            st.markdown("---")
            st.subheader("Download Reports")
            forecast_df = pd.DataFrame({'date': [forecast_date_main], 'value': [forecasted_level_main]})
            forecast_df['type'] = 'forecasted'
            
            hist_df_copy = historical_df.copy()
            hist_df_copy['type'] = 'historical'
            download_df = pd.concat([hist_df_copy[['date', 'value', 'type']], forecast_df], ignore_index=True)
            csv_data = download_df.to_csv(index=False).encode('utf-8')
            
            common_inputs = {'rainfall': rainfall, 'rfif': rfif, 'base_daily_pumping': pumping, 'specific_yield': specific_yield, 'assessment_area': area}
            researcher_inputs = {k: st.session_state[k] for k in policy_inputs}
            dss_outputs = {'projected_net_availability_MCM': f"{(max(0, final_net_availability) * 1000):.2f}",
                           'projected_stage_of_extraction_percent': f"{calculate_stage_of_extraction(final_draft, final_recharge):.2f}"}
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(label="Download Data (CSV)", data=csv_data, file_name=f"report_{current_well_no}.csv", mime="text/csv")
            with dl_col2:
                if st.button("Generate Report (PDF)"):
                    with st.spinner("Generating..."):
                        if 'meta_row' in locals():
                            pdf_data = create_report(current_well_no, meta_row, historical_df, common_inputs, researcher_inputs, dss_outputs, fig_forecast)
                            st.session_state.pdf_data = pdf_data
                        else:
                            st.error("Cannot generate PDF without well metadata.")
            if 'pdf_data' in st.session_state and st.session_state.pdf_data:
                st.download_button(label="Download PDF", data=st.session_state.pdf_data, file_name=f"report_{current_well_no}.pdf", mime="application/pdf")

        st.markdown('</div>', unsafe_allow_html=True)

    with researcher_tab:
        render_intervention_view("researcher")

    with policymaker_tab:
        render_intervention_view("policy_maker")

    with planners_tab:
        # The planner view includes the intervention levers, impact, and custom forecast...
        render_intervention_view("planner") 
        # ...and adds the new sustainability assessment section.
        render_sustainability_assessment()