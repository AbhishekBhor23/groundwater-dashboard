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

# --- MODIFIED: GitHub Configuration Updated ---
GITHUB_USERNAME = "AbhishekBhor23"
GITHUB_REPOSITORY = "groundwater-dashboard"
BRANCH_NAME = "main" # Or "master", depending on your repo

# --- Map Data (using filenames from your previous screenshot) ---
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

# Create a two-column layout that stacks on mobile
col1, col2 = st.columns(2)

# Loop through the map files and display them in the columns
for i, map_file in enumerate(map_files):
    # Construct the full URL to the raw image on GitHub
    image_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPOSITORY}/{BRANCH_NAME}/FINAL_MAPS/{map_file}"
    
    # Get a clean title from the filename
    map_title = map_file.replace('.png', '').replace('_', ' ')
    
    # Alternate between column 1 and column 2
    if i % 2 == 0:
        with col1:
            st.image(image_url, caption=f"Fig {i+1}: {map_title}", use_column_width=True)
            st.markdown("---")
    else:
        with col2:
            st.image(image_url, caption=f"Fig {i+1}: {map_title}", use_column_width=True)
            st.markdown("---")

# --- Final Conclusion Map ---
st.markdown("### Final Potential Recharge Zones Map")
final_map_file = "GWPZ.png" # Using the filename from your screenshot
final_image_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPOSITORY}/{BRANCH_NAME}/FINAL_MAPS/{final_map_file}"

st.image(final_image_url, caption="Final map showing areas with high potential for groundwater recharge.", use_column_width=True)

