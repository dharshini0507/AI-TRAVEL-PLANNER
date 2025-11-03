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
            font-family: 'Poppins', sans-serif;
        }
        h1 {
            text-align: center;
            font-size: 3rem !important;
            font-weight: 800;
            background: linear-gradient(90deg, #6a0dad, #8a2be2, #b57edc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        h2, h3 {
            text-align: center;
            font-weight: 700;
            background: linear-gradient(90deg, #7a1fa2, #9c4dcc, #c77dff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
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
        .block-container {max-width: 950px; margin: auto; padding-top: 2rem;}
    </style>
""", unsafe_allow_html=True)

# -------------------- HEADER --------------------
st.markdown("""
<h1>🌎 AI TRIP PLANNER ✈️</h1>
<p style='text-align:center;'>Your Smart, Budget-Friendly Travel Companion 💜</p>
""", unsafe_allow_html=True)

# -------------------- API CONFIG --------------------
API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    API_KEY = st.text_input("🔑 Enter your Google API Key", type="password")
if not API_KEY:
    st.warning("⚠️ Please enter your Google API key to continue.")
    st.stop()
genai.configure(api_key=API_KEY)

# -------------------- CHUNKED GENERATE FUNCTION --------------------
def chunked_generate(prompt_text, model_name="models/gemini-2.5-flash", chunk_size=1500):
    """Generates long text safely in chunks using Gemini 2.5 Flash."""
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        return f"[❌ Model initialization failed: {e}]"

    chunks = textwrap.wrap(prompt_text, chunk_size)
    results = []
    for c in chunks:
        try:
            response = model.generate_content(c)
            if hasattr(response, "text"):
                results.append(response.text)
        except Exception as e:
            results.append(f"[⚠️ Error generating chunk: {e}]")
    return "\n".join(results)

# -------------------- PDF FUNCTION --------------------
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in text.split("\n"):
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe_line)
    return BytesIO(pdf.output(dest="S").encode("latin-1"))

# -------------------- INPUT SECTION --------------------
st.markdown("<div class='section-box'><h2>📝 Plan Your Trip</h2>", unsafe_allow_html=True)

country = st.text_input("🌍 Country", value="India")
city = st.text_input("🏙️ City", value="Goa")
days = st.number_input("🗓️ Number of Days", 1, 15, 5)
budget = st.number_input("💰 Budget (USD)", 100, 20000, 1500)
travel_date = st.date_input("📅 Start Date", date.today())
interests = st.multiselect("🎯 Interests", ["Nature", "Adventure", "Food", "Culture", "Beaches", "History", "Shopping"])
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- MAIN ACTION --------------------
if st.button("🌸 Generate My AI Travel Plan"):
    if not country or not city or not interests:
        st.error("⚠️ Please fill all fields.")
    else:
        with st.spinner("✨ Crafting your perfect itinerary..."):
            prompt = f"""
            You are a professional AI travel planner.
            Create a detailed {days}-day travel itinerary for {city}, {country}, starting {travel_date}.
            Include the following sections clearly:
            1️⃣ Trip Summary (brief intro)
            2️⃣ Day-wise Itinerary (Morning, Afternoon, Evening)
            3️⃣ Budget Breakdown (Total ${budget}, daily estimate, categories)
            4️⃣ Top 3 Hotels & Restaurants (with short descriptions)
            5️⃣ Smart Travel Tips (5 tips on safety, local customs, best time, etc.)
            Interests: {', '.join(interests)}.
            """

            result = chunked_generate(prompt)

        st.success(f"✅ Travel Plan for {city}, {country} Ready!")

        # -------------------- DISPLAY SECTIONS --------------------
        def section(title, key):
            st.markdown(f"### {title}")
            if key in result:
                st.markdown(result.split(key)[-1].split("**")[0])
            else:
                st.markdown("⚠️ Section not generated.")
            st.markdown("---")

        section("1️⃣ Trip Summary", "1️⃣")
        section("2️⃣ Day-wise Itinerary", "2️⃣")
        section("3️⃣ Budget Breakdown", "3️⃣")
        section("4️⃣ Top 3 Hotels & Restaurants", "4️⃣")
        section("5️⃣ Smart Travel Tips", "5️⃣")

        # -------------------- MAP VIEW --------------------
        st.markdown('<div class="section-box"><h3>📍 Map View of Destination</h3>', unsafe_allow_html=True)
        try:
            df = pd.read_csv("worldcities.csv")
            if {'city', 'lat', 'lng'}.issubset(df.columns):
                city_data = df[df['city'].str.lower() == city.lower()]
                if not city_data.empty:
                    lat, lon = city_data.iloc[0]['lat'], city_data.iloc[0]['lng']
                    city_df = pd.DataFrame([{'lat': lat, 'lon': lon, 'city': city}])

                    st.pydeck_chart(pdk.Deck(
                        map_style="mapbox://styles/mapbox/streets-v12",
                        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=10, pitch=45),
                        layers=[
                            pdk.Layer(
                                "ScatterplotLayer",
                                data=city_df,
                                get_position='[lon, lat]',
                                get_color='[200, 100, 255]',
                                get_radius=5000,
                                pickable=True
                            )
                        ],
                        tooltip={"text": f"{city}, {country}"}
                    ))
                else:
                    st.warning(f"City '{city}' not found in worldcities.csv.")
            else:
                st.error("CSV must include columns: city, lat, lng.")
        except Exception as e:
            st.error(f"⚠️ Error showing map: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- DOWNLOAD --------------------
        st.markdown('<div class="section-box"><h3>📄 Download Plan</h3>', unsafe_allow_html=True)
        pdf_data = create_pdf(result)
        st.download_button(
            label="📄 Download Full Trip Plan (PDF)",
            data=pdf_data,
            file_name=f"{city}_AI_TravelPlan.pdf",
            mime="application/pdf"
        )
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- FOOTER --------------------
st.markdown("<hr><center>💜 AI Journey Planner | </center>", unsafe_allow_html=True)
