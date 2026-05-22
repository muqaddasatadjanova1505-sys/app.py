import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
from google.oauth2 import service_account

# 1. Sahifa ko'rinishi sozlamalari (Keng ekran rejimi)
st.set_page_config(layout="wide")
st.title("Google Earth Engine Web Map")

# 2. Earth Engine autentifikatsiyasi (Hamma xatoliklar tuzatilgan yakuniy qism)
try:
    # Streamlit Secrets'dan TOML formatidagi ma'lumotlarni olamiz
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # PEM va MalformedFraming xatolarini oldini olish uchun \n belgilarini to'g'rilaymiz
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    # invalid_scope xatosini yo'qotish uchun aniq ruxsatnomalar (scopes) yuklaymiz
    scopes = [
        'https://www.googleapis.com/auth/earthengine', 
        'https://www.googleapis.com/auth/cloud-platform'
    ]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    # Earth Engine-ni yangi ruxsatnoma bilan xavfsiz ishga tushiramiz
    if not ee.data.is_initialized():
        ee.Initialize(credentials=credentials)
except Exception as e:
    st.error(f"Google Earth Engine bilan bogʻlanishda xatolik yuz berdi: {e}")
    st.stop()

st.subheader("Interaktiv Xarita")

# 3. Standart Folium xaritasini yaratish (O'zbekiston / Xorazm atrofida)
m = folium.Map(location=[41.5, 61.0], zoom_start=7, control_scale=True)

# 4. Earth Engine qatlamlarini Folium xaritasiga qo'shish funksiyasi
def add_ee_layer(ee_image_object, vis_params, name):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        overlay=True,
        control=True
    ).add_to(m)

# 5. Earth Engine-dan relyef (DEM) ma'lumotlarini yuklab xaritaga qo'shish
try:
    dem = ee.Image('USGS/SRTMGL1_003')
    vis_params = {
        'min': 0,
        'max': 1500,
        'palette': ['blue', 'green', 'yellow', 'brown', 'white']
    }
    
    # Qatlamni xaritaga joylaymiz
    add_ee_layer(dem, vis_params, 'SRTM DEM Elevation')
    
    # Xaritada qatlamlarni yoqib-o'chirish (Layer Control) tugmachasini hosil qilamiz
    folium.LayerControl().add_to(m)

except Exception as e:
    st.warning(f"Earth Engine qatlamini yuklashda xatolik: {e}")

# 6. Tayyor xaritani Streamlit interfeysida ko'rsatish
st_folium(m, width="100%", height=600)
