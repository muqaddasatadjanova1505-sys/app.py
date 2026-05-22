import streamlit as st

# 1. Handle imports safely to avoid breaking the application
try:
    import ee
    import geemap.foliumap as geemap
    from google.oauth2 import service_account
except Exception as e:
    st.error(f"Error loading mapping modules: {e}")
    st.stop()

# Set up page layout
st.set_page_config(layout="wide")
st.title("Google Earth Engine Web Map")

# 2. Authenticate Earth Engine using Streamlit Secrets
try:
    # Convert Streamlit TOML secrets to a standard Python dict
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Create credentials
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    
    # Initialize Earth Engine with the service account credentials
    if not ee.data.is_initialized():
        ee.Initialize(credentials=credentials)
    
except Exception as e:
    st.error(f"Failed to authenticate with Google Earth Engine: {e}")
    st.stop()

# 3. Create and display your interactive map
st.subheader("Interactive Map View")

# Initialize a geemap Folium Map object
Map = geemap.Map(center=[41.5, 61.0], zoom=7)  # Centers around your target region

# Example: Add a standard Earth Engine dataset (Terrain Elevation)
dem = ee.Image('USGS/SRTMGL1_003')
vis_params = {
    'min': 0,
    'max': 1500,
    'palette': ['blue', 'green', 'yellow', 'brown', 'white']
}
Map.addLayer(dem, vis_params, 'SRTM DEM Elevation')

# Render the map inside the Streamlit web layout
Map.to_streamlit(height=600)
