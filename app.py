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

# -------------------- COORDINATES --------------------
df = pd.read_csv("worldcities.csv")

# Create dictionary of coordinates
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
st.markdown("""
<div class='section-box'>
<h2 style="text-align:center; font-weight:700;">
<span>📝</span> 
<span style="background: linear-gradient(90deg, #7a1fa2, #9c4dcc, #c77dff);
-webkit-background-clip: text; -webkit-text-fill-color: transparent;
text-shadow: 0 0 20px rgba(155, 89, 182, 0.7);">
Plan Your Trip
</span>
</h2>
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
        with st.spinner("✨ Creating your personalized travel plan..."):
            prompt = f"""
            You are a professional and experienced travel planner AI.
            Create a highly detailed, well-structured travel plan for the following input:

            Destination: {city}, {country}
            Duration: {days} days
            Start Date: {travel_date}
            Total Budget: ${budget} USD
            Traveler Interests: {', '.join(interests)}

            --- STRUCTURE YOUR RESPONSE EXACTLY LIKE THIS ---

            **1️⃣ Trip Summary**
            Write a short, engaging 2-3 paragraph introduction about {city}, describing:
            - Its culture, vibe, and best time to visit.
            - Why it's great for travelers with interests in {', '.join(interests)}.
            - A brief highlight of what this trip will cover.

            **2️⃣ Day-wise Itinerary**
            Write a day-by-day travel plan for {days} days.
            For each day, include:
            - **Day X: [Theme or Area Name]**
            - **Morning:** Activities, must-see attractions, or experiences (be realistic and locally accurate).
            - **Afternoon:** Local food or sightseeing plans.
            - **Evening:** Cultural experiences, shopping, or nightlife.
            - **Estimated Cost:** Mention approximate cost for that day in USD.

            Make sure each day's plan feels continuous and fits traveler interests (like {', '.join(interests)}).

            **3️⃣ Budget Breakdown (Total: ${budget} USD)**
            Create a breakdown with approximate costs in bullet or table form like:
            - Accommodation: $...
            - Food: $...
            - Transportation: $...
            - Sightseeing/Activities: $...
            - Miscellaneous: $...
            - **Total Estimated: ${budget} USD**

            **4️⃣ Top 5 Hotels & Restaurants**
            List:
            - 5 Recommended Hotels: (Name + Why they are good)
            - 5 Recommended Restaurants: (Name + Must-try dishes)

            **5️⃣ 5 Useful Travel Tips**
            Give 5 short, smart, destination-relevant travel tips.
            Example: safety, weather, transport, local etiquette, or packing advice.

            ---
            Use friendly and professional tone. Make it readable and visually formatted.
            """

            result = chunked_generate(prompt)

        st.success(f"✅ Your AI Travel Plan for {city}, {country} is Ready!")

        # -------------------- DISPLAY IN ORDER --------------------
        def extract_section(text, start, end=None):
            try:
                if end:
                    return text.split(start)[-1].split(end)[0].strip()
                else:
                    return text.split(start)[-1].strip()
            except Exception:
                return "⚠️ Section not properly generated."

        # Trip Summary
        st.markdown('<div class="section-box"><h3>1️⃣ Trip Summary</h3>', unsafe_allow_html=True)
        st.markdown(extract_section(result, "**1️⃣", "**2️⃣"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Day-wise Itinerary
        st.markdown('<div class="section-box"><h3>2️⃣ Day-wise Itinerary</h3>', unsafe_allow_html=True)
        st.markdown(extract_section(result, "**2️⃣", "**3️⃣"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Budget Breakdown
        st.markdown('<div class="section-box"><h3>3️⃣ Budget Breakdown</h3>', unsafe_allow_html=True)
        st.markdown(extract_section(result, "**3️⃣", "**4️⃣"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Hotels & Restaurants
        st.markdown('<div class="section-box"><h3>4️⃣ Top 5 Hotels & Restaurants</h3>', unsafe_allow_html=True)
        st.markdown(extract_section(result, "**4️⃣", "**5️⃣"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Travel Tips
        st.markdown('<div class="section-box"><h3>5️⃣ Useful Travel Tips</h3>', unsafe_allow_html=True)
        st.markdown(extract_section(result, "**5️⃣"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- MAP VIEW --------------------
        st.markdown('<div class="section-box"><h3>📍 City Map View</h3>', unsafe_allow_html=True)
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
        st.pydeck_chart(pdk.Deck(map_style="light", initial_view_state=view_state, layers=[glow_layer, layer], tooltip={"text": f"{city}, {country}"}))
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



