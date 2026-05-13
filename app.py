import streamlit as st

# Sahifaning asosi
st.set_page_config(page_title="Mening birinchi saytim", page_icon="🚀")

# Sarlavha
st.title("Assalomu alaykum! 🌟")

# Oddiy matn
st.write(f"Bu mening birinchi veb-saytim. Men buni Python dasturini o'rnatmasdan turib yaratdim!")

# Foydalanuvchi bilan muloqot
ism = st.text_input("Ismingizni kiriting:")

if ism:
    st.success(f"Salom {ism}! Saytimga xush kelibsiz. Ishlaringiz muvaffaqiyatli bo'lsin!")
    st.balloons() # Bayramona sharlar chiqadi

# Pastki qism
st.divider()
st.info("Bu sayt GitHub va Streamlit hamkorligida ishlamoqda.")
