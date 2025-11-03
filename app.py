import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
from datetime import date
import textwrap
import pydeck as pdk
import pandas as pd
import os

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="🌎 AI Travel Planner", page_icon="✈️", layout="wide")

# -------------------- STYLING --------------------
st.markdown("""
    <style>
        @keyframes pastelGradient {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        .stApp {
            background: linear-gradient(-45deg, #ece6ff, #f5e6ff, #ffe6fa, #e8faff);
            background-size: 400% 400%;
            animation: pastelGradient 20s ease infinite;
            color: #333;
            font-family: 'Poppins', sans-serif;
        }
        h1 {
            text-align: center;
            font-size: 3rem !important;
            font-weight: 800;
            background: linear-gradient(90deg, #6a0dad, #8a2be2, #b57edc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 25px rgba(140, 60, 200, 0.6);
        }
        h2, h3 {
            text-align: center;
            font-weight: 700;
            background: linear-gradient(90deg, #7a1fa2, #9c4dcc, #c77dff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(155, 89, 182, 0.7);
        }
        .section-box {
            background: rgba(255, 255, 255, 0.75);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 0 25px rgba(170, 140, 255, 0.25);
        }
        div.stButton > button {
            background: linear-gradient(90deg, #a678f5, #c084fc, #d8b4fe);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.8rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 0 20px rgba(180, 120, 255, 0.6);
            transition: all 0.3s ease-in-out;
        }
        div.stButton > button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px rgba(190, 130, 255, 0.8);
        }
        input, textarea, select {
            background-color: rgba(255, 255, 255, 0.6) !important;
            border: 1px solid rgba(155, 89, 182, 0.5) !important;
            border-radius: 10px !important;
            color: #333 !important;
        }
        .block-container {
            max-width: 950px;
            margin: auto;
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------- HEADER --------------------
st.markdown("""
<h1 style='text-align:center; font-weight:800; font-size:3rem;'>
<span>🌎</span> 
<span style="background: linear-gradient(90deg, #6a0dad, #8a2be2, #b57edc);
-webkit-background-clip: text; -webkit-text-fill-color: transparent;
text-shadow: 0 0 25px rgba(140, 60, 200, 0.6);">
AI TRIP PLANNER
</span>
<span>✈️</span>
</h1>
""", unsafe_allow_html=True)

st.markdown("<p style='text-align:center;'>Your Smart, Budget-Friendly Travel Companion 💜</p>", unsafe_allow_html=True)

# -------------------- API CONFIG --------------------
API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    API_KEY = st.text_input("🔑 Enter your Google API Key", type="password")
if not API_KEY:
    st.warning("⚠️ Please enter your Google API key to continue.")
    st.stop()
genai.configure(api_key=API_KEY)

# ✅ FIXED MODEL INITIALIZATION
model = genai.GenerativeModel("gemini-1.5-pro")

# -------------------- COORDINATES --------------------
df = pd.read_csv("worldcities.csv")
city_coords = {row['city']: (row['lat'], row['lng']) for _, row in df.iterrows()}

# -------------------- PDF FUNCTION --------------------
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in text.split("\n"):
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe_line)
    pdf_output = pdf.output(dest="S").encode("latin-1")
    return BytesIO(pdf_output)

# -------------------- INPUT SECTION --------------------
st.markdown("""
<div class='section-box'>
<h2>📝 Plan Your Trip</h2>
""", unsafe_allow_html=True)

country = st.text_input("🌍 Country", value="India")
city = st.text_input("🏙️ City", value="Goa")
days = st.number_input("🗓️ Number of Days", min_value=1, max_value=15, value=5)
budget = st.number_input("💰 Budget (USD)", min_value=100, step=100)
travel_date = st.date_input("📅 Start Date", value=date.today())
interests = st.multiselect("🎯 Interests", ["Nature", "Beaches", "Adventure", "Food", "History", "Shopping", "Culture"])
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- GENERATE BUTTON --------------------
if st.button("🌸 Generate My AI Travel Plan"):
    if not country or not city or not interests:
        st.error("⚠️ Please fill all fields before generating your plan.")
    else:
        with st.spinner("✨ Creating your travel plan..."):
            prompt = f"""
            You are a professional AI travel planner.
            Create a concise, clear, day-wise travel plan for:
            City: {city}, {country}
            Duration: {days} days
            Date: {travel_date}
            Budget: ${budget}
            Interests: {', '.join(interests)}

            --- RESPONSE FORMAT ---

            **1️⃣ Trip Summary (5 lines max)**
            **2️⃣ Day-wise Itinerary**
            **3️⃣ Budget Breakdown (Total ${budget})**
            **4️⃣ Top 3 Hotels & Restaurants**
            **5️⃣ 5 Smart Travel Tips**
            """

            response = model.generate_content(prompt)
            result = response.text.strip()

        st.success(f"✅ Your AI Travel Plan for {city}, {country} is Ready!")

        def show_section(title, content):
            st.markdown(f"### {title}")
            st.markdown(content)
            st.markdown("---")

        def extract_section(text, start, end=None):
            try:
                if end:
                    return text.split(start)[-1].split(end)[0].strip()
                else:
                    return text.split(start)[-1].strip()
            except Exception:
                return "⚠️ Section not properly generated."

        show_section("1️⃣ Trip Summary", extract_section(result, "**1️⃣", "**2️⃣"))
        show_section("2️⃣ Day-wise Itinerary", extract_section(result, "**2️⃣", "**3️⃣"))
        show_section("3️⃣ Budget Breakdown", extract_section(result, "**3️⃣", "**4️⃣"))
        show_section("4️⃣ Top 3 Hotels & Restaurants", extract_section(result, "**4️⃣", "**5️⃣"))
        show_section("5️⃣ Smart Travel Tips", extract_section(result, "**5️⃣"))

        # -------------------- MAP VIEW --------------------
        st.markdown('<div class="section-box"><h3>📍 World Cities Map View</h3>', unsafe_allow_html=True)
        try:
            if {'city', 'lat', 'lng'}.issubset(df.columns):
                st.success(f"✅ Loaded {len(df)} city coordinates from worldcities.csv!")

                df.rename(columns={'lng': 'lon'}, inplace=True)
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position='[lon, lat]',
                    get_color='[155, 89, 182, 180]',
                    get_radius=20000,
                    pickable=True,
                )
                glow_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position='[lon, lat]',
                    get_color='[210, 150, 255, 80]',
                    get_radius=40000,
                )

                center_lat = df['lat'].mean()
                center_lon = df['lon'].mean()

                view_state = pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=1.5,
                    pitch=0
                )

                st.pydeck_chart(pdk.Deck(
                    map_style="mapbox://styles/mapbox/light-v9",
                    initial_view_state=view_state,
                    layers=[glow_layer, layer],
                    tooltip={"text": "{city}\nLat: {lat}\nLon: {lon}"}
                ))
            else:
                st.error("❌ 'worldcities.csv' must include 'city', 'lat', and 'lng' columns.")
        except Exception as e:
            st.error(f"⚠️ Error loading map data: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- PDF DOWNLOAD --------------------
        st.markdown('<div class="section-box"><h3>📄 Download Your Trip Plan</h3>', unsafe_allow_html=True)
        pdf_file = create_pdf(result)
        st.download_button(
            label="📄 Download Full Trip Plan (PDF)",
            data=pdf_file,
            file_name=f"{city}_AI_TravelPlan.pdf",
            mime="application/pdf"
        )
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- FOOTER --------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<center>💜 AI Journey | ✈️</center>", unsafe_allow_html=True)
