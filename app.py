import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
from datetime import date
import textwrap
import pydeck as pdk

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
            background: linear-gradient(-45deg, #e8e4ff, #f5e6ff, #ffe6fa, #e8faff);
            background-size: 400% 400%;
            animation: pastelGradient 20s ease infinite;
            color: #333;
            font-family: 'Poppins', sans-serif;
        }
        h1 {
            text-align: center;
            font-size: 3rem !important;
            font-weight: 800;
            background: linear-gradient(90deg, #a66cff, #b19cd9, #d6b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 18px rgba(150, 90, 200, 0.4);
        }
        h2, h3 {
            text-align: center;
            background: linear-gradient(90deg, #d78fff, #b19cd9, #e8baff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 15px rgba(200, 150, 255, 0.4);
        }
        .section-box {
            background: rgba(255, 255, 255, 0.75);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 0 20px rgba(170, 140, 255, 0.2);
        }
        div.stButton > button {
            background: linear-gradient(90deg, #c5a3ff, #e8baff, #fbd8ff);
            color: #333;
            border: none;
            border-radius: 12px;
            padding: 0.7rem 1.4rem;
            font-weight: 600;
            box-shadow: 0 0 15px rgba(200, 150, 255, 0.5);
            transition: all 0.3s ease-in-out;
        }
        div.stButton > button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 25px rgba(200, 150, 255, 0.8);
        }
        input, textarea, select {
            background-color: rgba(255, 255, 255, 0.6) !important;
            border: 1px solid rgba(155, 89, 182, 0.4) !important;
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
st.markdown("<h1>✨ AI JOURNEY ✈️</h1>", unsafe_allow_html=True)
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
city_coords = {
    # 🇮🇳 INDIA
    "Bangalore": (12.9716, 77.5946),
    "Goa": (15.2993, 74.1240),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Kolkata": (22.5726, 88.3639),
    "Jaipur": (26.9124, 75.7873),
    "Pune": (18.5204, 73.8567),
    "Ahmedabad": (23.0225, 72.5714),
    "Mysore": (12.2958, 76.6394),
    "Mangalore": (12.9141, 74.8560),
    "Cochin": (9.9312, 76.2673),
    "Ooty": (11.4064, 76.6932),
    "Manali": (32.2396, 77.1887),
    "Leh": (34.1526, 77.5771),
    "Shimla": (31.1048, 77.1734),
    "Varanasi": (25.3176, 82.9739),
    "Rishikesh": (30.0869, 78.2676),
    "Gokarna": (14.5500, 74.3167),
    "Byndoor": (13.8667, 74.6333),
    "Madurai": (9.9252, 78.1198),
    "Tirupati": (13.6288, 79.4192),
    "Vizag": (17.6868, 83.2185),

    # 🇪🇺 EUROPE
    "Paris": (48.8566, 2.3522),
    "London": (51.5072, -0.1276),
    "Rome": (41.9028, 12.4964),
    "Zurich": (47.3769, 8.5417),
    "Berlin": (52.5200, 13.4050),
    "Madrid": (40.4168, -3.7038),
    "Barcelona": (41.3851, 2.1734),
    "Amsterdam": (52.3676, 4.9041),
    "Vienna": (48.2082, 16.3738),
    "Prague": (50.0755, 14.4378),
    "Budapest": (47.4979, 19.0402),
    "Athens": (37.9838, 23.7275),
    "Venice": (45.4408, 12.3155),
    "Munich": (48.1351, 11.5820),
    "Lisbon": (38.7169, -9.1399),
    "Dublin": (53.3498, -6.2603),
    "Copenhagen": (55.6761, 12.5683),
    "Oslo": (59.9139, 10.7522),
    "Stockholm": (59.3293, 18.0686),
    "Brussels": (50.8503, 4.3517),
    "Warsaw": (52.2297, 21.0122),

    # 🇺🇸 NORTH AMERICA
    "New York": (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "San Francisco": (37.7749, -122.4194),
    "Chicago": (41.8781, -87.6298),
    "Miami": (25.7617, -80.1918),
    "Las Vegas": (36.1699, -115.1398),
    "Washington DC": (38.9072, -77.0369),
    "Boston": (42.3601, -71.0589),
    "Houston": (29.7604, -95.3698),
    "Seattle": (47.6062, -122.3321),
    "Toronto": (43.6511, -79.3470),
    "Vancouver": (49.2827, -123.1207),
    "Montreal": (45.5017, -73.5673),
    "Mexico City": (19.4326, -99.1332),

    # 🇦🇸 ASIA
    "Tokyo": (35.6762, 139.6503),
    "Seoul": (37.5665, 126.9780),
    "Bangkok": (13.7563, 100.5018),
    "Singapore": (1.3521, 103.8198),
    "Kuala Lumpur": (3.1390, 101.6869),
    "Hong Kong": (22.3193, 114.1694),
    "Beijing": (39.9042, 116.4074),
    "Shanghai": (31.2304, 121.4737),
    "Taipei": (25.0330, 121.5654),
    "Manila": (14.5995, 120.9842),
    "Dubai": (25.276987, 55.296249),
    "Doha": (25.2854, 51.5310),
    "Bali": (-8.3405, 115.0920),
    "Kathmandu": (27.7172, 85.3240),
    "Colombo": (6.9271, 79.8612),
    "Hanoi": (21.0285, 105.8542),
    "Phuket": (7.8804, 98.3923),
    "Jaipur": (26.9124, 75.7873),

    # 🌏 OCEANIA
    "Sydney": (-33.8688, 151.2093),
    "Melbourne": (-37.8136, 144.9631),
    "Auckland": (-36.8485, 174.7633),
    "Brisbane": (-27.4698, 153.0251),
    "Perth": (-31.9505, 115.8605),
    "Fiji": (-17.7134, 178.0650),
    "Christchurch": (-43.5321, 172.6362),

    # 🌍 AFRICA
    "Cairo": (30.0444, 31.2357),
    "Cape Town": (-33.9249, 18.4241),
    "Nairobi": (-1.2921, 36.8219),
    "Marrakesh": (31.6295, -7.9811),
    "Casablanca": (33.5731, -7.5898),
    "Accra": (5.6037, -0.1870),
    "Lagos": (6.5244, 3.3792),
    "Durban": (-29.8587, 31.0218),

    # 🇧🇷 SOUTH AMERICA
    "Rio de Janeiro": (-22.9068, -43.1729),
    "São Paulo": (-23.5505, -46.6333),
    "Buenos Aires": (-34.6037, -58.3816),
    "Lima": (-12.0464, -77.0428),
    "Santiago": (-33.4489, -70.6693),
    "Bogota": (4.7110, -74.0721),
    "Quito": (-0.1807, -78.4678),
    "Caracas": (10.4806, -66.9036),
}
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
st.markdown('<div class="section-box"><h2>📝 Plan Your Trip</h2>', unsafe_allow_html=True)
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

        # Display plan
        st.markdown('<div class="section-box"><h3>🗺️ Complete Trip Plan</h3>', unsafe_allow_html=True)
        st.write(result)
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- MAP VIEW --------------------
        st.markdown('<div class="section-box"><h3>📍 City Map View</h3>', unsafe_allow_html=True)
        if city in city_coords:
            lat, lon = city_coords[city]
        else:
            st.warning(f"⚠️ No exact coordinates found for {city}. Showing India map.")
            lat, lon = (20.5937, 78.9629)

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{"lat": lat, "lon": lon}],
            get_position='[lon, lat]',
            get_color='[240, 60, 0, 200]',
            get_radius=6000,
        )

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/pastel-day-v11',
            initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=8, pitch=30),
            layers=[layer],
            tooltip={"text": f"{city}, {country}"}
        ))
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- PDF DOWNLOAD --------------------
        pdf_file = create_pdf(result)
        st.download_button(
            "📄 Download Full Trip Plan (PDF)",
            data=pdf_file,
            file_name=f"{city}_AI_TravelPlan.pdf",
            mime="application/pdf"
        )

# -------------------- FOOTER --------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<center>💜 AI Journey | Pastel Glow Edition | Powered by Gemini ✈️</center>", unsafe_allow_html=True)
