import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
from google.oauth2 import service_account

# 1. Sahifa ko'rinishi sozlamalari
st.set_page_config(layout="wide")
st.title("Xorazm Viloyati NDVI Klassifikatsiyasi (4 Klass)")

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

st.subheader("Gidrografiyasiz, 4 ta klassga ajratilgan hududlar xaritasi")

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
    
    # 6. 4 TA KLASSIFIKATSIYA ZONASI (Gidrografiyasiz)
    # Boshlang'ich qiymat: barcha ochiq yerlar, qum va suvlar 1-klassga o'tadi (NDVI <= 0.2)
    classified_ndvi = ee.Image(1)
    
    # NDVI 0.2 dan 0.35 gacha -> Class 2 (Siyrak o'simlik va yaylovlar)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.2).And(raw_ndvi.lte(0.35)), 2)
    
    # NDVI 0.35 dan 0.55 gacha -> Class 3 (O'rtacha rivojlangan ekinlar)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.35).And(raw_ndvi.lte(0.55)), 3)
    
    # NDVI 0.55 dan yuqori bo'lsa -> Class 4 (Zich va qalin ekinzorlar, bog'lar)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.55), 4)
    
    # Tasvirni chegaraga qirqish
    classified_ndvi = classified_ndvi.clip(xorazm_boundary)

    # 7. Vizualizatsiya parametrlari (4 ta aniq rang)
    class_vis = {
        'min': 1,
        'max': 4,
        'palette': [
            '#D3B39C',  # 1-klass: Ochiq tuproq, qumliklar va bino/inshootlar (Och jigarrang)
            '#FFFF00',  # 2-klass: Siyrak o'simlik qoplami (Sariq)
            '#7CFC00',  # 3-klass: O'rtacha zichlikdagi ekinlar (Och yashil)
            '#006400'   # 4-klass: Yuqori zichlikdagi ekinlar va bog'lar (To'q yashil)
        ]
    }
    
    # Qatlamni xaritaga qo'shish
    add_ee_layer(classified_ndvi, class_vis, 'Xorazm 4 Klassli NDVI')
    folium.LayerControl().add_to(m)

except Exception as e:
    st.warning(f"Klassifikatsiyada xatolik: {e}")

# 8. Xaritani ko'rsatish
st_folium(m, width="100%", height=650)

# 9. Shartli Belgilar (Legend)
st.markdown("""
### 📊 Xarita Shartli Belgilari (4 Klass):
* 🟫 **Och jigarrang (1):** Ekin ekilmagan bo'sh yerlar, sho'rxoklar, qumliklar va shahar/aholi punktlari.
* 🟨 **Sariq (2):** Siyrak o'simliklar, tabiiy o'tloqlar yoki vegetatsiyasi yakunlangan g'alla maydonlari.
* 🟩 **Och yashil (3):** O'rtacha rivojlanish darajasidagi qishloq xo'jaligi ekinlari (g'o'za va b.).
* 🌲 **To'q yashil (4):** Juda zich rivojlangan yashil ekinzorlar, bog'lar, to'qaylar va daraxtzorlar.
""")
