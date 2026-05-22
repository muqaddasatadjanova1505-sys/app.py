import streamlit as st
import ee
import geemap.foliumap as geemap
import folium
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import base64
from io import StringIO

# Sahifa sozlamalari
st.set_page_config(
    page_title="Xorazm Viloyati - Vegetatsiya Monitoringi",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS uslublar
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a5f;
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4a5568;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    .info-box {
        background-color: #f7fafc;
        border-left: 5px solid #667eea;
        padding: 1rem;
        border-radius: 0 10px 10px 0;
        margin: 1rem 0;
    }
    .stButton>button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Google Earth Engine ni ishga tushirish
try:
    ee.Initialize(project='ee-your-project')
except:
    st.error("GEE autentifikatsiya xatosi! Iltimos, service account sozlamalarini tekshiring.")

# Xorazm viloyati chegaralari
xorazm_region = ee.Geometry.Rectangle([59.5, 41.0, 61.5, 42.0])

# Tumanlar ma'lumotlari
districts_data = {
    "Urganch": {"center": [41.55, 60.63], "area": 320},
    "Xiva": {"center": [41.38, 60.36], "area": 450},
    "Hazorasp": {"center": [41.32, 61.08], "area": 380},
    "Shovot": {"center": [41.65, 60.00], "area": 410},
    "Gurlan": {"center": [41.85, 60.40], "area": 350},
    "Xonqa": {"center": [41.47, 60.72], "area": 390},
    "Bog'ot": {"center": [41.33, 60.85], "area": 340},
    "Qo‘shko‘pir": {"center": [41.53, 60.35], "area": 370},
    "Yangiariq": {"center": [41.30, 60.55], "area": 360},
    "Yangibozor": {"center": [41.73, 60.55], "area": 330},
    "Tuproqqal'a": {"center": [41.58, 60.78], "area": 300}
}

# Asosiy sarlavha
st.markdown('<h1 class="main-header">🛰️ Xorazm Viloyati Vegetatsiya Monitoring Tizimi</h1>', unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Landsat 8/9 Sun\'iy Yo'ldosh Ma'lumotlari Asosida NDVI/NDWI/EVI Indekslarini Tahlil</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Flag_of_Xorazm_Region.png/120px-Flag_of_Xorazm_Region.png", width=100)
    st.title("⚙️ Sozlamalar")

    # Vaqt oralig'i
    st.subheader("📅 Vaqt Oralig'i")
    start_date = st.date_input("Boshlanish sanasi", datetime(2024, 3, 1))
    end_date = st.date_input("Tugash sanasi", datetime(2024, 9, 30))

    # Indeks tanlash
    st.subheader("📊 Vegetatsiya Indeksi")
    index_type = st.selectbox(
        "Indeksni tanlang:",
        ["NDVI - Normalized Difference Vegetation Index",
         "NDWI - Normalized Difference Water Index", 
         "EVI - Enhanced Vegetation Index",
         "SAVI - Soil Adjusted Vegetation Index"]
    )

    # Bulutlarni filtrlash
    cloud_cover = st.slider("Bulut qoplami (%)", 0, 100, 20)

    # Tuman tanlash
    st.subheader("🗺️ Hudud Tanlash")
    selected_districts = st.multiselect(
        "Tumanlarni tanlang (barchasi uchun bo'sh qoldiring):",
        list(districts_data.keys()),
        default=[]
    )

    # Tahlil tugmasi
    analyze_btn = st.button("🔍 Tahlilni Boshlash", use_container_width=True)

# Asosiy kontent
if analyze_btn:
    with st.spinner("Sun'iy yo'ldosh ma'lumotlari yuklanmoqda..."):

        # Landsat 8 Collection 2 ma'lumotlarini olish
        collection = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                     .filterBounds(xorazm_region)
                     .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                     .filter(ee.Filter.lt('CLOUD_COVER', cloud_cover))
                     .sort('CLOUD_COVER'))

        if collection.size().getInfo() == 0:
            st.warning("Tanlangan vaqt oralig'ida ma'lumot topilmadi. Iltimos, boshqa sanalarni tanlang.")
        else:
            # Eng kam bulutli tasvirni tanlash
            image = collection.median()

            # Indekslarni hisoblash
            if "NDVI" in index_type:
                # NDVI = (NIR - Red) / (NIR + Red)
                # Landsat 8: B5=NIR, B4=Red
                index = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
                vis_params = {'min': -0.2, 'max': 0.8, 'palette': ['#a50026', '#d73027', '#f46d43', '#fdae61', '#fee090', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695']}
                index_name = "NDVI"

            elif "NDWI" in index_type:
                # NDWI = (Green - NIR) / (Green + NIR)
                # Landsat 8: B3=Green, B5=NIR
                index = image.normalizedDifference(['SR_B3', 'SR_B5']).rename('NDWI')
                vis_params = {'min': -0.5, 'max': 0.5, 'palette': ['#8B4513', '#D2691E', '#F4A460', '#87CEEB', '#4682B4', '#191970']}
                index_name = "NDWI"

            elif "EVI" in index_type:
                # EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
                # Landsat 8: B5=NIR, B4=Red, B2=Blue
                evi = image.expression(
                    '2.5 * (NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1)',
                    {'NIR': image.select('SR_B5'), 'RED': image.select('SR_B4'), 'BLUE': image.select('SR_B2')}
                ).rename('EVI')
                index = evi
                vis_params = {'min': -0.2, 'max': 1.0, 'palette': ['#ffffcc', '#c2e699', '#78c679', '#31a354', '#006837']}
                index_name = "EVI"

            else:  # SAVI
                # SAVI = (1+L)(NIR-Red)/(NIR+Red+L) where L=0.5
                savi = image.expression(
                    '(1 + 0.5) * (NIR - RED) / (NIR + RED + 0.5)',
                    {'NIR': image.select('SR_B5'), 'RED': image.select('SR_B4')}
                ).rename('SAVI')
                index = savi
                vis_params = {'min': -0.2, 'max': 0.8, 'palette': ['#d73027', '#fc8d59', '#fee08b', '#d9ef8b', '#91cf60', '#1a9850']}
                index_name = "SAVI"

            # Statistik ma'lumotlarni olish
            stats = index.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.minMax(),
                    sharedInputs=True
                ),
                geometry=xorazm_region,
                scale=30,
                maxPixels=1e9
            ).getInfo()

            # Tumanlar bo'yicha statistika
            district_stats = []
            for district, info in districts_data.items():
                if not selected_districts or district in selected_districts:
                    point = ee.Geometry.Point(info["center"][::-1])
                    district_value = index.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=point.buffer(5000),
                        scale=30
                    ).getInfo()

                    district_stats.append({
                        "Tuman": district,
                        f"{index_name} O'rtacha": district_value.get(index_name.lower(), 0),
                        "Maydoni (km²)": info["area"]
                    })

            df_stats = pd.DataFrame(district_stats)

            # 1-qator: Xarita va statistika
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"🗺️ {index_name} Xaritasi")

                # Folium xaritasi
                m = geemap.Map(center=[41.55, 60.63], zoom=9)
                m.addLayer(index, vis_params, index_name)
                m.addLayerControl()

                # Tuman markazlarini qo'shish
                for district, info in districts_data.items():
                    if not selected_districts or district in selected_districts:
                        folium.Marker(
                            location=info["center"],
                            popup=f"<b>{district}</b><br>Maydon: {info['area']} km²",
                            icon=folium.Icon(color='red', icon='info-sign')
                        ).add_to(m)

                m.to_streamlit(height=500)

            with col2:
                st.subheader("📊 Umumiy Statistika")

                # Asosiy ko'rsatkichlar
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("O'rtacha", f"{stats.get(index_name.lower() + '_mean', 0):.3f}")
                with col_m2:
                    st.metric("Standart Og'ish", f"{stats.get(index_name.lower() + '_stdDev', 0):.3f}")

                col_m3, col_m4 = st.columns(2)
                with col_m3:
                    st.metric("Minimum", f"{stats.get(index_name.lower() + '_min', 0):.3f}")
                with col_m4:
                    st.metric("Maksimum", f"{stats.get(index_name.lower() + '_max', 0):.3f}")

                # Tumanlar bo'yicha jadval
                st.subheader("📋 Tumanlar Bo'yicha")
                st.dataframe(df_stats, use_container_width=True, hide_index=True)

            # 2-qator: Diagrammalar
            st.markdown("---")
            st.subheader("📈 Vizual Tahlil")

            col3, col4 = st.columns(2)

            with col3:
                # Tumanlar bo'yicha bar chart
                fig_bar = px.bar(
                    df_stats,
                    x="Tuman",
                    y=f"{index_name} O'rtacha",
                    color=f"{index_name} O'rtacha",
                    color_continuous_scale="Viridis",
                    title=f"Tumanlar Bo'yicha {index_name} Taqqoslash",
                    template="plotly_white"
                )
                fig_bar.update_layout(
                    xaxis_tickangle=-45,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col4:
                # Maydon va indeks o'rtasidagi munosabat
                fig_scatter = px.scatter(
                    df_stats,
                    x="Maydoni (km²)",
                    y=f"{index_name} O'rtacha",
                    size=f"{index_name} O'rtacha",
                    color="Tuman",
                    title=f"Maydon va {index_name} Munosabati",
                    template="plotly_white",
                    size_max=50
                )
                fig_scatter.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            # 3-qator: Vaqt seriyasi va yuklab olish
            st.markdown("---")

            # Vaqt seriyasi tahlili
            st.subheader("⏱️ Vaqt Seriyasi Tahlili")

            # Oylik o'rtacha qiymatlar
            months = pd.date_range(start_date, end_date, freq='MS')
            monthly_data = []

            for month in months:
                month_start = month.strftime('%Y-%m-%d')
                month_end = (month + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime('%Y-%m-%d')

                monthly_collection = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                                    .filterBounds(xorazm_region)
                                    .filterDate(month_start, month_end)
                                    .filter(ee.Filter.lt('CLOUD_COVER', cloud_cover)))

                if monthly_collection.size().getInfo() > 0:
                    monthly_image = monthly_collection.median()

                    if "NDVI" in index_type:
                        monthly_index = monthly_image.normalizedDifference(['SR_B5', 'SR_B4'])
                    elif "NDWI" in index_type:
                        monthly_index = monthly_image.normalizedDifference(['SR_B3', 'SR_B5'])
                    elif "EVI" in index_type:
                        monthly_index = monthly_image.expression(
                            '2.5 * (NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1)',
                            {'NIR': monthly_image.select('SR_B5'), 'RED': monthly_image.select('SR_B4'), 'BLUE': monthly_image.select('SR_B2')}
                        )
                    else:
                        monthly_index = monthly_image.expression(
                            '(1 + 0.5) * (NIR - RED) / (NIR + RED + 0.5)',
                            {'NIR': monthly_image.select('SR_B5'), 'RED': monthly_image.select('SR_B4')}
                        )

                    monthly_mean = monthly_index.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=xorazm_region,
                        scale=30
                    ).getInfo()

                    monthly_data.append({
                        "Oy": month.strftime('%Y-%m'),
                        f"{index_name}": list(monthly_mean.values())[0] if monthly_mean else None
                    })

            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data)

                fig_line = px.line(
                    df_monthly,
                    x="Oy",
                    y=f"{index_name}",
                    markers=True,
                    title=f"Oylik {index_name} Dinamikasi",
                    template="plotly_white"
                )
                fig_line.update_traces(line=dict(width=3), marker=dict(size=10))
                fig_line.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_line, use_container_width=True)

            # Ma'lumotlarni yuklab olish
            st.markdown("---")
            st.subheader("💾 Ma'lumotlarni Yuklab Olish")

            col5, col6, col7 = st.columns(3)

            with col5:
                # CSV formatida
                csv = df_stats.to_csv(index=False)
                st.download_button(
                    label="📄 CSV Formatida Yuklash",
                    data=csv,
                    file_name=f"xorazm_{index_name.lower()}_statistika.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with col6:
                # JSON formatida
                json_data = df_stats.to_json(orient='records', force_ascii=False)
                st.download_button(
                    label="📋 JSON Formatida Yuklash",
                    data=json_data,
                    file_name=f"xorazm_{index_name.lower()}_statistika.json",
                    mime="application/json",
                    use_container_width=True
                )

            with col7:
                # Excel formatida
                excel_buffer = StringIO()
                df_stats.to_excel(excel_buffer, index=False, engine='openpyxl')
                excel_data = excel_buffer.getvalue()
                st.download_button(
                    label="📊 Excel Formatida Yuklash",
                    data=excel_data,
                    file_name=f"xorazm_{index_name.lower()}_statistika.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            # Qo'shimcha ma'lumotlar
            st.markdown("---")
            st.subheader("ℹ️ Indeks Haqida Ma'lumot")

            if "NDVI" in index_type:
                st.info("""
                **NDVI (Normalized Difference Vegetation Index)** - vegetatsiyaning umumiy holatini ko'rsatadi.
                - **-0.2 dan 0 gacha**: Suv, qor, bulut
                - **0 dan 0.2 gacha**: Tuproq, qurigan o'simliklar
                - **0.2 dan 0.4 gacha**: Kam vegetatsiya (o'tloqlar)
                - **0.4 dan 0.6 gacha**: O'rta vegetatsiya (dalalar)
                - **0.6 dan 0.8 gacha**: Yuqori vegetatsiya (o'rmonlar)
                """)
            elif "NDWI" in index_type:
                st.info("""
                **NDWI (Normalized Difference Water Index)** - suv resurslarini aniqlash uchun ishlatiladi.
                - **-0.5 dan 0 gacha**: Qurug'lik, tuproq
                - **0 dan 0.2 gacha**: Nam tuproq
                - **0.2 dan 0.5 gacha**: Suv jismonlari, daryolar, ko'llar
                """)
            elif "EVI" in index_type:
                st.info("""
                **EVI (Enhanced Vegetation Index)** - zich vegetatsiyali hududlarda NDVI dan aniqroq natija beradi.
                - **-0.2 dan 0.2 gacha**: Vegetatsiya yo'q
                - **0.2 dan 0.4 gacha**: Kam vegetatsiya
                - **0.4 dan 0.6 gacha**: O'rta vegetatsiya
                - **0.6 dan 1.0 gacha**: Yuqori vegetatsiya
                """)
            else:
                st.info("""
                **SAVI (Soil Adjusted Vegetation Index)** - tuproq ta'sirini kamaytirish uchun ishlatiladi.
                - **-0.2 dan 0.2 gacha**: Vegetatsiya yo'q
                - **0.2 dan 0.4 gacha**: Kam vegetatsiya
                - **0.4 dan 0.6 gacha**: O'rta vegetatsiya
                - **0.6 dan 0.8 gacha**: Yuqori vegetatsiya
                """)

else:
    # Boshlang'ich holat
    st.markdown("""
    <div class="info-box">
        <h3>👋 Xush kelibsiz!</h3>
        <p>Bu ilova <b>Xorazm viloyati</b> hududida sun'iy yo'ldosh ma'lumotlari asosida vegetatsiya indekslarini tahlil qilish uchun yaratilgan.</p>
        <p><b>Asosiy imkoniyatlar:</b></p>
        <ul>
            <li>🛰️ Landsat 8/9 sun'iy yo'ldosh ma'lumotlaridan foydalanish</li>
            <li>📊 NDVI, NDWI, EVI, SAVI indekslarini hisoblash</li>
            <li>🗺️ Interaktiv xaritalar orqali vizualizatsiya</li>
            <li>📈 Vaqt seriyasi bo'yicha dinamik tahlil</li>
            <li>📋 Tumanlar bo'yicha statistik hisobotlar</li>
            <li>💾 CSV, JSON, Excel formatlarida yuklab olish</li>
        </ul>
        <p><b>Boshlash uchun:</b> Chap paneldan vaqt oralig'ini, indeksni va tumanlarni tanlab, "Tahlilni Boshlash" tugmasini bosing.</p>
    </div>
    """, unsafe_allow_html=True)

    # Namuna xarita
    st.subheader("🗺️ Xorazm Viloyati Tumanlari")

    # Namuna ma'lumotlar bilan xarita
    sample_data = []
    for district, info in districts_data.items():
        sample_data.append({
            "Tuman": district,
            "Kenglik": info["center"][0],
            "Uzunlik": info["center"][1],
            "Maydoni (km²)": info["area"]
        })

    df_sample = pd.DataFrame(sample_data)

    fig_map = px.scatter_mapbox(
        df_sample,
        lat="Kenglik",
        lon="Uzunlik",
        size="Maydoni (km²)",
        color="Tuman",
        hover_name="Tuman",
        zoom=8,
        height=500,
        title="Xorazm Viloyati Tumanlari (Namuna)"
    )
    fig_map.update_layout(mapbox_style="carto-positron")
    st.plotly_chart(fig_map, use_container_width=True)

    # Tumanlar jadvali
    st.subheader("📋 Tumanlar Ma'lumotlari")
    st.dataframe(df_sample, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🛰️ <b>Xorazm Vegetatsiya Monitoring Tizimi</b> | Landsat 8/9 + Google Earth Engine + Streamlit</p>
    <p>© 2024 | Amaliy Ish</p>
</div>
""", unsafe_allow_html=True)
