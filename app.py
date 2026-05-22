import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
from google.oauth2 import service_account

# 1. Sahifa ko'rinishi sozlamalari
st.set_page_config(layout="wide")
st.title("Xorazm Viloyati NDVI Klassifikatsiyasi (Sentinel-2)")

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

st.subheader("Klassifikatsiya qilingan hududlar")

# 3. Folium xaritasini yaratish
m = folium.Map(location=[41.50, 60.60], zoom_start=9, control_scale=True)

def add_ee_layer(ee_image_object, vis_params, name):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True
    ).add_to(m)

# 4. Xorazm chegarasini aniqlash
countries = ee.FeatureCollection("FAO/GAUL/2015/level2")
xorazm_boundary = countries.filter(ee.Filter.eq('ADM1_NAME', 'Khorezm'))

# 5. Sentinel-2 tasviri va NDVI hisoblash
try:
    s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterBounds(xorazm_boundary)
                     .filterDate('2025-06-01', '2025-08-31')
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))
    
    s2_image = s2_collection.median()
    raw_ndvi = s2_image.normalizedDifference(['B8', 'B4']).clip(xorazm_boundary)
    
    # ⚠️ 6. NDVI KLASSIFIKATSIYASI (Hududlarni sinflarga ajratish)
    # Boshlang'ich qiymat sifatida barcha piksellarni 1 (Suv yoki bo'sh yer) deb olamiz
    classified_ndvi = ee.Image(1)
    
    # Shartlar bo'yicha zonalarga ajratamiz:
    # NDVI 0.1 dan 0.2 gacha bo'lsa -> Class 2 (Qumloq va sho'rxok yerlar)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.1).And(raw_ndvi.lte(0.2)), 2)
    
    # NDVI 0.2 dan 0.35 gacha bo'lsa -> Class 3 (Siyrak o'simlik va yaylovlar)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.35).And(raw_ndvi.lte(0.5)), 3)
    
    # NDVI 0.35 dan 0.5 gacha bo'lsa -> Class 4 (O'rtacha rivojlangan ekinlar)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.5).And(raw_ndvi.lte(0.65)), 4)
    
    # NDVI 0.5 dan yuqori bo'lsa -> Class 5 (Sersuv, zich va qalin yashil ekinzorlar)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.65), 5)
    
    # Klassifikatsiyalangan tasvirni Xorazm chegarasiga qirqamiz
    classified_ndvi = classified_ndvi.clip(xorazm_boundary)

    # 7. Vizualizatsiya parametrlari (Har bir klass uchun alohida keskin rang)
    # 1: Moviy (Suv), 2: Och jigarrang (Ochiq tuproq/Qum), 3: Sariq (Siyrak), 4: Och yashil (O'rtacha), 5: To'q yashil (Zich)
    class_vis = {
        'min': 1,
        'max': 5,
        'palette': [
            '#0000FF',  # 1-klass: Suv (Moviy)
            '#DEB887',  # 2-klass: Bo'sh yer / Qum (Jigarrang)
            '#FFFF00',  # 3-klass: Siyrak o'simlik (Sariq)
            '#7CFC00',  # 4-klass: O'rtacha ekin (Och yashil)
            '#006400'   # 5-klass: Qalin ekinzor (To'q yashil)
        ]
    }
    
    # Qatlamni xaritaga qo'shish
    add_ee_layer(classified_ndvi, class_vis, 'Xorazm NDVI Klassifikatsiyasi')
    folium.LayerControl().add_to(m)

except Exception as e:
    st.warning(f"Klassifikatsiyada xatolik: {e}")

# 8. Xaritani ko'rsatish
st_folium(m, width="100%", height=650)

# 9. Streamlit interfeysida tushuntirish (Legend) oynasi yaratish
st.markdown("""
### 📊 Xarita Shartli Belgilari (Legend):
* 🟦 **Moviy (1):** Suv havzalari (Daryo, ko'llar va kanallar).
* 🟫 **Och jigarrang (2):** Ekin ekilmagan bo'sh yerlar, sho'rxoklar yoki qumliklar.
* 🟨 **Sariq (3):** Siyrak o'simlik qoplami, pishib yetilgan g'alla yoki o'tloqlar.
* 🟩 **Och yashil (4):** O'rtacha rivojlanish bosqichidagi g'o'za va boshqa qishloq xo'jaligi ekinlari.
* FFE 🟩 **To'q yashil (5):** Juda zich va intensiv rivojlangan yashil ekinzorlar, bog'lar va to'qaylar.
""")
