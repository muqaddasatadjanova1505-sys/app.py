import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
from google.oauth2 import service_account

# 1. Sahifa ko'rinishi sozlamalari
st.set_page_config(layout="wide")
st.title("Xorazm Viloyati NDVI Xaritasi (Sentinel-2)")

# 2. Earth Engine autentifikatsiyasi
try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scopes = [
        'https://www.googleapis.com/auth/earthengine', 
        'https://www.googleapis.com/auth/cloud-platform'
    ]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    if not ee.data.is_initialized():
        ee.Initialize(credentials=credentials)
except Exception as e:
    st.error(f"Google Earth Engine bilan bogʻlanishda xatolik yuz berdi: {e}")
    st.stop()

st.subheader("Interaktiv NDVI va Relyef Xaritasi")

# 3. Folium xaritasini aynan Xorazm markaziga to'g'irlab yaratamiz
# [41.50, 60.60] koordinatasi Xorazmni xarita markaziga olib keladi
m = folium.Map(location=[41.50, 60.60], zoom_start=9, control_scale=True)

# 4. Earth Engine qatlamini Folium xaritasiga qo'shish funksiyasi
def add_ee_layer(ee_image_object, vis_params, name):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        overlay=True,
        control=True
    ).add_to(m)

# 5. Xorazm viloyati chegarasini olish (FAO GAUL o'tish kodi orqali)
# Uzbekistan - Khorezm viloyati filtrlash
countries = ee.FeatureCollection("FAO/GAUL/2015/level2")
xorazm_boundary = countries.filter(ee.Filter.eq('ADM1_NAME', 'Khorezm'))

# 6. Sentinel-2 tasvirlarini yuklash va NDVI hisoblash
try:
    # 2025-yil yoz oylaridagi eng kam bulutli Sentinel-2 tasvirlarini yig'amiz
    s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterBounds(xorazm_boundary)
                     .filterDate('2025-06-01', '2025-08-31')
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))
    
    # Tasvirlarning o'rtacha qiymatini (Median) olamiz
    s2_image = s2_collection.median()
    
    # NDVI formulasini hisoblaymiz: (B8 - B4) / (B8 + B4)
    # Sentinel-2 da: B8 - Yaqin infraqizil (NIR), B4 - Qizil (Red)
    ndvi = s2_image.normalizedDifference(['B8', 'B4']).clip(xorazm_boundary)
    
    # NDVI vizualizatsiya parametrlari (Qizil - haydalgan yer/qum, Sariq - siyrak o'simlik, Yashil - qalin ekinlar)
    ndvi_vis = {
        'min': 0.0,
        'max': 0.7,
        'palette': [
            '#FFFFFF', '#CE7E45', '#DF923D', '#F1B555', '#FCD163', '#99B718',
            '#74A901', '#66A200', '#529400', '#3E8601', '#207401', '#056201',
            '#004C00', '#023B01', '#012E01', '#011D01', '#011301'
        ]
    }
    
    # NDVI qatlamini xaritaga qo'shish
    add_ee_layer(ndvi, ndvi_vis, 'Xorazm NDVI (Sentinel-2)')

    # Qo'shimcha ravishda eski Relyef (DEM) qatlamini ham zaxira sifatida qo'shib qo'yamiz (Xorazmga kesilgan holda)
    dem = ee.Image('USGS/SRTMGL1_003').clip(xorazm_boundary)
    dem_vis = {'min': 0, 'max': 200, 'palette': ['blue', 'green', 'yellow', 'brown']}
    add_ee_layer(dem, dem_vis, 'SRTM DEM Relyef')

    # Qatlamlarni yoqib-o'chirish boshqaruvini qo'shish
    folium.LayerControl().add_to(m)

except Exception as e:
    st.warning(f"NDVI ma'lumotlarini hisoblashda xatolik yuz berdi: {e}")

# 7. Xaritani Streamlit ekraniga chiqarish
st_folium(m, width="100%", height=650)
