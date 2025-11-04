import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
from datetime import date
import textwrap
import pydeck as pdk
import pandas as pd
import time

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

# -------------------- FAST GENERATE FUNCTION --------------------
def generate_fast(prompt_text, model_name="models/gemini-2.5-flash"):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"[❌ Error: {e}]"

# -------------------- PDF FUNCTION --------------------
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
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
        with st.spinner("🧭 Planning your dream trip..."):
            prompt = f"""
You are a professional travel planner.
Generate a detailed {days}-day travel itinerary for {city}, {country}, starting on {travel_date}.

✈️ Focus on: {', '.join(interests)}.
🪔 Currency: Indian Rupees (₹).

🗺️ Trip Summary: 4–5 line vibe description.

📅 Day-wise Itinerary:
For each day, include:

- **Morning:** Start time + place + what to do + small highlight
- **Afternoon:** Next attraction / market / activity + include approx travel time or distance
- **Evening:** Sunset spot / café / dinner / chill activity suggestion
- **Food Suggestions:** Mention 1 breakfast place, 1 lunch spot, 1 dinner spot (name only, no long description)

💰 Budget: total within ₹{int(budget * 83)}, per day ~₹{round((budget * 83) / days)}

🏨 Hotels: 3 best stays (name + location + approx ₹/night)
🍽️ Restaurants: 3 best local food spots (name + cuisine + must try dish)

💡 Travel Tips: exactly 5 bullet points
"""
            result = generate_fast(prompt)   # ✅ Correctly Indented

# -------------------- DISPLAY OUTPUT --------------------
        st.success(f"✅ Travel Plan for {city}, {country} Ready!")
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown(result)   # ✅ fast normal output
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------- MAP VIEW --------------------
        st.markdown('<div class="section-box"><h3>📍 Map View of Destination</h3>', unsafe_allow_html=True)

        try:
            df = pd.read_csv("worldcities.csv")

            if {'city', 'lat', 'lng'}.issubset(df.columns):
                city_data = df[df['city'].str.lower() == city.lower()]

                if not city_data.empty:
                    lat = float(city_data.iloc[0]['lat'])
                    lon = float(city_data.iloc[0]['lng'])
                    city_df = pd.DataFrame([{'lat': lat, 'lon': lon, 'city': city}])

                    st.pydeck_chart(pdk.Deck(
                        initial_view_state=pdk.ViewState(
                            latitude=lat,
                            longitude=lon,
                            zoom=10,
                            pitch=0
                        ),
                        layers=[
                            pdk.Layer(
                                "TileLayer",
                                data=None,
                                get_tile_url="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
                                tile_size=256
                            ),
                            pdk.Layer(
                                "ScatterplotLayer",
                                data=city_df,
                                get_position='[lon, lat]',
                                get_color='[255, 75, 150, 200]',
                                get_radius=3000,
                                pickable=True
                            ),
                            pdk.Layer(
                                "TextLayer",
                                data=city_df,
                                get_position='[lon, lat]',
                                get_text='city',
                                get_color='[255, 255, 255, 255]',
                                get_size=24,
                                get_alignment_baseline='"bottom"'
                            )
                        ],
                        tooltip={"text": f"📍 {city}, {country}\nLat: {lat:.2f}, Lon: {lon:.2f}"}
                    ))

                    st.success(f"🗺️ Showing {city}, {country} on the map!")
                else:
                    st.warning(f"⚠️ City '{city}' not found in worldcities.csv.")
            else:
                st.error("CSV file must include columns: city, lat, lng.")

        except Exception as e:
            st.error(f"⚠️ Error showing map: {e}")

        st.markdown('</div>', unsafe_allow_html=True)


        # -------------------- DOWNLOAD PDF --------------------
        st.markdown('<div class="section-box"><h3>📄 Download Trip Plan</h3>', unsafe_allow_html=True)
        pdf_data = create_pdf(result)
        st.download_button(
            label="📄 Download Full Trip Plan (PDF)",
            data=pdf_data,
            file_name=f"{city}_AI_TravelPlan.pdf",
            mime="application/pdf"
        )
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- FOOTER --------------------
st.markdown("<hr><center>💜 AI Journey Planner |✨</center>", unsafe_allow_html=True)









