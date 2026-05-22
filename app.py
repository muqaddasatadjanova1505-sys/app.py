import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
from google.oauth2 import service_account

# Sahifa sozlamalari
st.set_page_config(layout="wide")
st.title("Google Earth Engine Web Map (Stable Version)")

# 1. Earth Engine autentifikatsiyasi (Streamlit Secrets orqali)
try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    
    if not ee.data.is_initialized():
        ee.Initialize(credentials=credentials)
except Exception as e:
    st.error(f"Google Earth Engine bilan bogʻlanishda xatolik: {e}")
    st.stop()

st.subheader("Interaktiv Xarita")

# 2. Standart Folium xaritasini yaratish (Xorazm/Oʻzbekiston koordinatalari atrofida)
# [41.5, 61.0] - hudud markazi
m = folium.Map(location=[41.5, 61.0], zoom_start=7, control_scale=True)

# 3. Earth Engine qatlamini Folium xaritasiga qoʻshish funksiyasi
def add_ee_layer(ee_image_object, vis_params, name):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        overlay=True,
        control=True
    ).add_to(m)

# 4. Misol tariqasida relyef (DEM) ma'lumotini yuklash
try:
    dem = ee.Image('USGS/SRTMGL1_003')
    vis_params = {
        'min': 0,
        'max': 1500,
        'palette': ['blue', 'green', 'yellow', 'brown', 'white']
    }
    
    # Earth Engine qatlamini xaritaga qo'shish
    add_ee_layer(dem, vis_params, 'SRTM DEM Elevation')
    
    # Qatlamlarni yoqib-ochirish tugmasini qo'shish
    folium.LayerControl().add_to(m)

except Exception as e:
    st.warning(f"Earth Engine qatlamini yuklashda xatolik: {e}")

# 5. Xaritani Streamlit sahifasida ko'rsatish
st_folium(m, width="100%", height=600)
