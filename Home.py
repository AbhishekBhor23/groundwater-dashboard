import streamlit as st
from PIL import Image

# --- Page Configuration ---
st.set_page_config(
    page_title="Groundwater Management Portal",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Theme Selection ---
# Initialize session state for theme if it doesn't exist
if 'theme' not in st.session_state:
    st.session_state.theme = "Dark" # Default theme

# --- Custom CSS for Dark and Light Themes ---
dark_theme_css = """
<style>
    /* Main App Background */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #C9D1D9;
    }
    /* Specific styling for containers if you use them */
    .st-emotion-cache-1r6slb0 {
        background-color: #1C212E;
    }
</style>
"""

light_theme_css = """
<style>
    /* Main App Background */
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #111111;
    }
    /* Specific styling for containers if you use them */
    .st-emotion-cache-1r6slb0 {
        background-color: #F0F2F6;
    }
</style>
"""

# --- Sidebar ---
st.sidebar.title("Settings")
# Theme selector radio button
# A callback function updates the session state when the radio button is changed
def theme_changed():
    st.session_state.theme = st.session_state.theme_selector

selected_theme = st.sidebar.radio(
    "Select Theme",
    ["Dark", "Light"],
    key="theme_selector",
    on_change=theme_changed,
    index=0 if st.session_state.theme == "Dark" else 1 # Set default based on session state
)

# Apply selected theme's CSS
st.markdown(dark_theme_css if st.session_state.theme == "Dark" else light_theme_css, unsafe_allow_html=True)


# --- Home Page Content ---
st.title("Welcome to the Groundwater Management Portal 💧")
st.markdown("---")
st.header("An Integrated Platform for Groundwater Analysis and Decision Support")

st.markdown("""
This portal is a comprehensive tool designed for various stakeholders involved in water resource management. It provides in-depth analysis of historical groundwater data and a powerful **Groundwater Management Suite (GMS)** to model and forecast future scenarios.

Navigate through the different sections using the sidebar to explore the features tailored for your needs.
""")

# You can uncomment this section and provide a path to an image if you have one
# try:
#     image = Image.open('your_image_path.png')
#     st.image(image, caption='Groundwater System Diagram')
# except FileNotFoundError:
#     st.info("Info: An illustrative image could be placed here.")


st.subheader("How to Use This Portal")
st.markdown("""
1.  **Select a Well:** Start by navigating to the **Data Analytics** page. Use the "Find a Well" feature in the sidebar to select a specific well by State, District, Block, and Village.

2.  **Analyze Historical Data:** Once a well is selected, the **Data Analytics** page will display its historical water level trends, yearly comparisons, and seasonal fluctuations.

3.  **Model Future Scenarios:** Go to the **Groundwater Management Suite** to use the interactive modeling tools. Adjust various hydrogeological and policy factors to see their impact on the future of the groundwater resources.

4.  **Get Recommendations:** Each module provides clear, color-coded recommendations and forecasts to support informed decision-making for farmers, researchers, and policymakers.
""")

st.info("Please begin by selecting a page from the sidebar on the left.")
