import streamlit as st

# --- Page Configuration ---
st.set_page_config(page_title="Regional DSS - Satara", page_icon="🗺️", layout="wide")

# --- Main Page Content ---
st.title("Regional DSS: Potential Recharge Zones 🗺️")
st.header("Satara District, Maharashtra")
st.markdown("---")
st.info(
    "This section displays the thematic maps used in the analysis to identify potential "
    "groundwater recharge zones within Satara District. Each map represents a different "
    "geospatial factor influencing groundwater accumulation."
)

# --- GitHub Configuration ---
# Details have been updated from your screenshot
GITHUB_USERNAME = "AbhishekBhor23"
GITHUB_REPOSITORY = "groundwater-dashboard"
BRANCH_NAME = "main" # This is usually 'main' or 'master'

# --- Map Data ---
# Filenames have been updated from your screenshot
map_files = [
    "DD.png",
    "Geomorphology.png",
    "LULC.png",
    "LD.png",
    "Lithology.png",
    "RF.png",
    "Slope.png"
]

# --- Display Maps in a Grid ---
st.markdown("### Thematic Maps for Analysis")

# Create a two-column layout that will stack automatically on mobile
col1, col2 = st.columns(2)

# Loop through the map files and display them in the columns
for i, map_file in enumerate(map_files):
    # Construct the full URL to the raw image on GitHub
    image_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPOSITORY}/{BRANCH_NAME}/FINAL_MAPS/{map_file}"
    
    # Get a clean title from the filename
    map_title = map_file.replace('.png', '').replace('_', ' ')
    
    # Alternate between column 1 and column 2 for a neat grid
    if i % 2 == 0:
        with col1:
            # CORRECTED: Using use_container_width instead of the deprecated use_column_width
            st.image(image_url, caption=f"Fig {i+1}: {map_title}", use_container_width=True)
            st.markdown("---")
    else:
        with col2:
            # CORRECTED: Using use_container_width instead of the deprecated use_column_width
            st.image(image_url, caption=f"Fig {i+1}: {map_title}", use_container_width=True)
            st.markdown("---")

# --- Final Conclusion Map ---
st.markdown("### Final Potential Recharge Zones Map")
final_map_file = "GWPZ.png"
final_image_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPOSITORY}/{BRANCH_NAME}/FINAL_MAPS/{final_map_file}"

# CORRECTED: Using use_container_width instead of the deprecated use_column_width
st.image(final_image_url, caption="Final map showing areas with high potential for groundwater recharge.", use_container_width=True)

