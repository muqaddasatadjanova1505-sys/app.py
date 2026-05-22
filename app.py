import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
from google.oauth2 import service_account

# 1. Sahifa ko'rinishi sozlamalari (Brauzer vkladkasidagi nom va keng ekran)
st.set_page_config(
    layout="wide", 
    page_title="Atadjanova Muqaddas | Web Mapping Final Project"
)

# Sahifaning eng tepasidagi asosiy sarlavha
st.title("Xorazm Viloyati Hududlarining NDVI Indeksini Klassifikatsiya Qilish")
st.write("Talaba: Atadjanova Muqaddas | Yoʻnalish: Web Kartalashtirish")

# 2. Earth Engine autentifikatsiyasi
try:
    # Streamlit Secrets'dan ma'lumotlarni olamiz
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # PEM va MalformedFraming xatolarini to'g'rilash
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    # Ruxsatnomalar (scopes) yuklash
    scopes = [
        'https://www.googleapis.com/auth/earthengine', 
        'https://www.googleapis.com/auth/cloud-platform'
    ]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    # Earth Engine-ni ishga tushirish
    if not ee.data.is_initialized():
        ee.Initialize(credentials=credentials)
except Exception as e:
    st.error(f"Google Earth Engine bilan bogʻlanishda xatolik yuz berdi: {e}")
    st.stop()

st.subheader("Interaktiv 4 Klassli NDVI Xaritasi")

# 3. Folium xaritasini yaratish (Xorazm markazida)
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

# 4. Xorazm chegarasini filtrlash
countries = ee.FeatureCollection("FAO/GAUL/2015/level2")
xorazm_boundary = countries.filter(ee.Filter.eq('ADM1_NAME', 'Khorezm'))

# 5. Sentinel-2 ma'lumotlarini yuklash va NDVI hisoblash
try:
    s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterBounds(xorazm_boundary)
                     .filterDate('2025-06-01', '2025-08-31')
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))
    
    s2_image = s2_collection.median()
    raw_ndvi = s2_image.normalizedDifference(['B8', 'B4']).clip(xorazm_boundary)
    
    # 6. 4 ta quruqlik klassiga ajratish (Gidrografiyasiz)
    classified_ndvi = ee.Image(1)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.2).And(raw_ndvi.lte(0.35)), 2)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.35).And(raw_ndvi.lte(0.55)), 3)
    classified_ndvi = classified_ndvi.where(raw_ndvi.gt(0.55), 4)
    
    classified_ndvi = classified_ndvi.clip(xorazm_boundary)

    # 7. Vizualizatsiya ranglari
    class_vis = {
        'min': 1,
        'max': 4,
        'palette': [
            '#D3B39C',  # 1-klass: Ochiq tuproq, qumliklar va aholi punktlari
            '#FFFF00',  # 2-klass: Siyrak o'simlik qoplami
            '#7CFC00',  # 3-klass: O'rtacha zichlikdagi ekinzorlar
            '#006400'   # 4-klass: Yuqori zichlikdagi qalin ekinlar va bog'lar
        ]
    }
    
    # Qatlamni yuklash
    add_ee_layer(classified_ndvi, class_vis, 'Xorazm 4 Klassli NDVI')
    folium.LayerControl().add_to(m)

except Exception as e:
    st.warning(f"Klassifikatsiyada xatolik yuz berdi: {e}")

# 8. Xaritani ko'rsatish
st_folium(m, width="100%", height=650)

# 9. Shartli Belgilar (Legend)
st.markdown("""
### 📊 Xarita Shartli Belgilari (Legend):
* 🟫 **Och jigarrang (1):** Ekin ekilmagan bo'sh yerlar, sho'rxoklar, qumliklar, yo'llar va bino/inshootlar.
* 🟨 **Sariq (2):** Siyrak o'simliklar, tabiiy o'tloqlar yoki hosili yig'ib olingan g'alla maydonlari.
* 🟩 **Och yashil (3):** O'rtacha rivojlanish darajasidagi qishloq xo'jaligi ekinlari (g'o'za, sabzavotlar va b.).
* 🌲 **To'q yashil (4):** Juda zich va jadal rivojlangan yashil ekinzorlar, intensiv bog'lar va to'qayzorlar.
""")
