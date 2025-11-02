import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
from datetime import date
import textwrap
import pydeck as pdk
import pandas as pd


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
st.markdown("<h1> 🌎 AI TRIP PLANNER ✈️</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Your Smart, Budget-Friendly Travel Companion 💜</p>", unsafe_allow_html=True)

# -------------------- API CONFIG --------------------
API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    API_KEY = st.text_input("🔑 Enter your Google API Key", type="password")
if not API_KEY:
    st.warning("⚠️ Please enter your Google API key to continue.")
    st.stop()
genai.configure(api_key=API_KEY)

# -------------------- COORDINATES --------------------
# -------------------- LOAD CITY COORDINATES --------------------
try:
    df_coords = pd.read_csv("city_coords.csv")
    city_coords = {row['city']: (row['latitude'], row['longitude']) for _, row in df_coords.iterrows()}
except Exception as e:
    st.warning(f"⚠️ Could not load city coordinates: {e}")
    city_coords = {}

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

# -------------------- GENERATION FUNCTION --------------------
def chunked_generate(prompt_text, model_name="gemini-2.5-flash", chunk_size=1500):
    model = genai.GenerativeModel(model_name)
    chunks = textwrap.wrap(prompt_text, chunk_size)
    results = []
    for c in chunks:
        try:
            response = model.generate_content(c)
            if hasattr(response, "text"):
                results.append(response.text)
        except Exception as e:
            results.append(f"[Error: {e}]")
    return "\n".join(results)

# -------------------- INPUT SECTION --------------------
st.markdown('<div class="section-box"><h2 class="blink-heading">📝 Plan Your Trip</h2>', unsafe_allow_html=True)
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
        with st.spinner("✨ Creating your personalized travel plan..."):
            prompt = f"""
            Generate a {days}-day travel plan for {city}, {country}, starting {travel_date}.
            Include:
            1. A short trip summary
            2. Day-wise itinerary
            3. A budget breakdown (Total ${budget})
            4. Top 5 hotel & restaurant recommendations
            5. 5 useful travel tips
            Focus on: {', '.join(interests)}.
            """
            result = chunked_generate(prompt)

        st.success(f"✅ Your AI Travel Plan for {city}, {country} is Ready!")

        # -------------------- SPLIT RESULT INTO SECTIONS --------------------
        sections = result.split("\n\n")
        trip_summary = ""
        itinerary = ""
        hotels = ""
        restaurants = ""
        tips = ""

        for sec in sections:
            s = sec.lower()
            if "summary" in s:
                trip_summary += sec + "\n\n"
            elif "day" in s:
                itinerary += sec + "\n\n"
            elif "hotel" in s:
                hotels += sec + "\n\n"
            elif "restaurant" in s:
                restaurants += sec + "\n\n"
            elif "tip" in s:
                tips += sec + "\n\n"

        # -------------------- COMPLETE TRIP PLAN --------------------
        st.markdown('<div class="section-box"><h3 class="blink-heading">🗺️ Complete Trip Plan</h3>', unsafe_allow_html=True)
        st.markdown(trip_summary + itinerary, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- HOTEL RECOMMENDATIONS --------------------
        st.markdown('<div class="section-box"><h3 class="blink-heading">🏨 Hotel Recommendations</h3>', unsafe_allow_html=True)
        if hotels:
            st.markdown(hotels, unsafe_allow_html=True)
        else:
            st.info("No specific hotel recommendations found.")
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- RESTAURANT RECOMMENDATIONS --------------------
        st.markdown('<div class="section-box"><h3 class="blink-heading">🍽️ Restaurant Suggestions</h3>', unsafe_allow_html=True)
        if restaurants:
            st.markdown(restaurants, unsafe_allow_html=True)
        else:
            st.info("No specific restaurant suggestions found.")
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- TRAVEL TIPS --------------------
        st.markdown('<div class="section-box"><h3 class="blink-heading">💡 Travel Tips</h3>', unsafe_allow_html=True)
        if tips:
            st.markdown(tips, unsafe_allow_html=True)
        else:
            st.info("No travel tips were generated.")
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- MAP VIEW --------------------
        st.markdown('<div class="section-box"><h3 class="blink-heading">📍 City Map View</h3>', unsafe_allow_html=True)
        if city in city_coords:
            lat, lon = city_coords[city]
            zoom_level = 8
        else:
            st.warning(f"⚠️ No exact coordinates found for {city}. Showing World Map.")
            lat, lon = (0, 0)
            zoom_level = 1

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{"lat": lat, "lon": lon}],
            get_position='[lon, lat]',
            get_color='[160, 32, 240, 230]',
            get_radius=40000,
        )

        glow_layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{"lat": lat, "lon": lon}],
            get_position='[lon, lat]',
            get_color='[210, 150, 255, 120]',
            get_radius=90000,
        )

        view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom_level, pitch=0)

        st.pydeck_chart(pdk.Deck(
            map_style="light",
            initial_view_state=view_state,
            layers=[glow_layer, layer],
            tooltip={"text": f"{city}, {country}"}
        ))
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- PDF DOWNLOAD --------------------
        st.markdown('<div class="section-box"><h3 class="blink-heading">📄 Download Your Trip Plan</h3>', unsafe_allow_html=True)
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
