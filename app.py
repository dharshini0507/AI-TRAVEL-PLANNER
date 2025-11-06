# app.py
import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
from datetime import date, datetime
import pydeck as pdk
import pandas as pd
import sqlite3
import hashlib
import json
import os

# -------------------- CONFIG --------------------
st.set_page_config(page_title="🌎 AI Travel Planner", page_icon="✈️", layout="wide")

TITLE = "AI TRAVEL PLANNER"
TAGLINE = "Plan smarter • Travel better • Powered by AI 💜"
DB_PATH = "travel_app.db"

# -------------------- GLOBAL STYLES --------------------
st.markdown("""
<style>
@keyframes pastelGradient { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
.stApp{
  background: linear-gradient(-45deg, #ece6ff, #f5e6ff, #ffe6fa, #e8faff);
  background-size: 400% 400%; animation: pastelGradient 18s ease infinite;
  font-family: 'Poppins', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}
.block-container{max-width: 980px; padding-top: 1.5rem;}
h1{
  text-align:center; font-size:3rem !important; font-weight:800;
  background: linear-gradient(90deg, #6a0dad, #8a2be2, #b57edc);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
h2,h3{
  text-align:center; font-weight:700;
  background: linear-gradient(90deg, #7a1fa2, #9c4dcc, #c77dff);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.section-box{
  background: rgba(255,255,255,0.78); border-radius: 22px; padding: 20px; margin-bottom: 22px;
  box-shadow: 0 0 25px rgba(170,140,255,0.25);
}
div.stButton>button{
  background: linear-gradient(90deg,#a678f5,#c084fc,#d8b4fe); color:#fff; border:none; border-radius:12px;
  padding:.8rem 1.2rem; font-weight:600; box-shadow:0 0 20px rgba(180,120,255,.6); transition:.25s;
}
div.stButton>button:hover{ transform:scale(1.04); box-shadow:0 0 30px rgba(190,130,255,.85); }
.muted{opacity:.85; font-size:.92rem; text-align:center}
.pill{display:inline-block;padding:4px 10px;border-radius:999px;background:#f1eaff;margin:2px;}
/* --- Login hero --- */
.hero-wrap{margin-top: 6vh; text-align:center;}
.hero-title{
  font-size:3.2rem; font-weight:900; letter-spacing:.5px;
  background: linear-gradient(90deg,#6c00ff,#b43dee,#ff79c6,#6c00ff);
  background-size: 300% 100%; -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  animation: titleflow 6s ease infinite;
}
@keyframes titleflow{0%{background-position:0%}50%{background-position:100%}100%{background-position:0%}}
.hero-tag{font-size:1.1rem; margin-top:6px; opacity:.9}
.glass-card{
  margin: 28px auto 10px auto; width: 480px; max-width: 92%;
  background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.35);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 18px 60px rgba(31,38,135,0.35);
  border-radius: 20px; padding: 26px 22px;
}
.hero-cta{margin-top:6px}
.small-tip{opacity:.7; font-size:.85rem; margin-top:6px}
.footer-mini{opacity:.75; text-align:center}
</style>
""", unsafe_allow_html=True)

# -------------------- API KEY (no prompt—secrets only) --------------------
try:
    API_KEY = st.secrets["general"]["GOOGLE_API_KEY"]
except Exception:
    st.error("🚫 Google API key not found in secrets. Add it to `.streamlit/secrets.toml` under [general] GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=API_KEY)

# -------------------- DB HELPERS --------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS trips(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            country TEXT, city TEXT, days INTEGER, budget_usd INTEGER,
            travel_date TEXT, interests TEXT, result_text TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    # seed user (optional)
    try:
        c.execute("INSERT INTO users(email,password_hash,name,created_at) VALUES (?,?,?,?)",
                  ("demo@example.com", hashlib.sha256("demo123".encode()).hexdigest(), "Demo User", datetime.utcnow().isoformat()))
    except sqlite3.IntegrityError:
        pass
    conn.commit(); conn.close()

def hash_pw(pw:str)->str: return hashlib.sha256(pw.encode()).hexdigest()

def signup_user(email, password, name=""):
    conn=get_conn(); c=conn.cursor()
    try:
        c.execute("INSERT INTO users(email,password_hash,name,created_at) VALUES (?,?,?,?)",
                  (email, hash_pw(password), name, datetime.utcnow().isoformat()))
        conn.commit(); return True, "Account created! Please log in."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()

def login_user(email, password):
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,password_hash,name FROM users WHERE email=?", (email,))
    row=c.fetchone(); conn.close()
    if row and row[1]==hash_pw(password):
        return {"id":row[0], "email":email, "name":row[2] or ""}
    return None

def save_trip(user_id,country,city,days,budget,travel_date,interests,result_text):
    conn=get_conn(); c=conn.cursor()
    c.execute("""INSERT INTO trips(user_id,country,city,days,budget_usd,travel_date,interests,result_text,created_at)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
              (user_id,country,city,int(days),int(budget),str(travel_date),json.dumps(interests),result_text,datetime.utcnow().isoformat()))
    conn.commit(); tid=c.lastrowid; conn.close(); return tid

def load_trips(user_id):
    conn=get_conn(); c=conn.cursor()
    c.execute("""SELECT id,country,city,days,budget_usd,travel_date,interests,created_at
                 FROM trips WHERE user_id=? ORDER BY id DESC""", (user_id,))
    rows=c.fetchall(); conn.close(); return rows

def load_trip_detail(trip_id, user_id):
    conn=get_conn(); c=conn.cursor()
    c.execute("""SELECT id,country,city,days,budget_usd,travel_date,interests,result_text,created_at
                 FROM trips WHERE id=? AND user_id=?""", (trip_id,user_id))
    row=c.fetchone(); conn.close(); return row

init_db()

# -------------------- AI + PDF --------------------
def generate_fast(prompt_text, model_name="models/gemini-2.5-flash"):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"[❌ Error: {e}]"

from fpdf import FPDF
def create_pdf(text):
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Helvetica", size=14)
    for line in (text or "").split("\n"):
        safe=line.encode('latin-1','replace').decode('latin-1'); pdf.multi_cell(0,8,safe)
    return BytesIO(pdf.output(dest="S").encode("latin-1"))

# -------------------- SESSION --------------------
if "user" not in st.session_state: st.session_state.user=None
if "last_result" not in st.session_state: st.session_state.last_result=""
if "last_inputs" not in st.session_state: st.session_state.last_inputs={}

# -------------------- AUTH (GLASS HERO) --------------------
def auth_screen():
    st.markdown(f"""
        <div class="hero-wrap">
            <div class="hero-title">🌎 {TITLE} ✈️</div>
            <div class="hero-tag">{TAGLINE}</div>
        </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔐 Login", "🆕 Sign Up"])

    with tab_login:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        colA,colB = st.columns([1,1])
        with colA:
            if st.button("✨ Login", use_container_width=True):
                user = login_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success("Logged in! Loading your planner...")
                    st.experimental_rerun()
                else:
                    st.error("Invalid email or password.")
        with colB:
            st.markdown('<div class="small-tip">Try: demo@example.com / demo123</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_signup:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name_su = st.text_input("Full Name")
        email_su = st.text_input("Email")
        pw_su = st.text_input("Password", type="password")
        pw2_su = st.text_input("Confirm Password", type="password")
        if st.button("🌟 Create Account", use_container_width=True):
            if not email_su or not pw_su:
                st.error("Please fill all fields.")
            elif pw_su != pw2_su:
                st.error("Passwords do not match.")
            else:
                ok,msg = signup_user(email_su, pw_su, name_su)
                st.success(msg) if ok else st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- MAIN APP --------------------
def app_main():
    user = st.session_state.user
    st.markdown(f"<p class='muted'>Signed in as <b>{user.get('name') or user['email']}</b></p>", unsafe_allow_html=True)

    # History
    with st.expander("📚 View Previous Plans"):
        trips = load_trips(user["id"])
        if not trips:
            st.info("No trips saved yet. Generate one and click **Save Plan**.")
        else:
            df_prev = pd.DataFrame([{
                "Trip ID": r[0], "Country": r[1], "City": r[2], "Days": r[3],
                "Budget (USD)": r[4], "Start Date": r[5],
                "Interests": ", ".join(json.loads(r[6] or "[]")),
                "Created": r[7][:19].replace("T"," ")
            } for r in trips])
            st.dataframe(df_prev, use_container_width=True)
            selected_id = st.number_input("Enter Trip ID to open", min_value=0, step=1, value=0)
            if st.button("Open Saved Trip"):
                if selected_id:
                    d = load_trip_detail(selected_id, user["id"])
                    if d:
                        _, country, city, days, budget, tdate, interests_js, result_text, created = d
                        st.success(f"Opened Trip #{selected_id}: {city}, {country}")
                        with st.container(border=True):
                            st.markdown(result_text if result_text else "_No content saved_")
                            st.download_button("📄 Download Full Trip Plan (PDF)",
                                               data=create_pdf(result_text),
                                               file_name=f"{city}_AI_TravelPlan.pdf",
                                               mime="application/pdf")
                    else:
                        st.error("Trip not found or not yours.")

    # Inputs
    st.markdown("<div class='section-box'><h2>📝 Plan Your Trip</h2>", unsafe_allow_html=True)
    country = st.text_input("🌍 Country", value="India")
    city = st.text_input("🏙️ City", value="Goa")
    days = st.number_input("🗓️ Number of Days", 1, 15, 5)
    budget = st.number_input("💰 Budget (USD)", 100, 20000, 1500)
    travel_date = st.date_input("📅 Start Date", date.today())
    interests = st.multiselect("🎯 Interests", ["Nature","Adventure","Food","Culture","Beaches","History","Shopping"])
    st.markdown("</div>", unsafe_allow_html=True)

    result = st.session_state.get("last_result","")

    # Generate
    if st.button("🌸 Generate My AI Travel Plan"):
        if not country or not city or not interests:
            st.error("⚠️ Please fill all fields.")
        else:
            with st.spinner("🧭 Planning your dream trip..."):
                # --- DO NOT CHANGE PROMPT CONTENT (kept exactly as requested) ---
                prompt = f"""
You are a professional travel planner.
Generate a detailed {days}-day travel itinerary for {city}, {country}, starting on {travel_date}.

✈️ Focus on: {', '.join(interests)}.
🪔 Currency: Indian Rupees (₹).

🗺️ Trip Summary: 3-4 line vibe description.

📅 Day-wise Itinerary:
For each day, include:

- **Morning:** Start time + place + what to do + small highlight
- **Afternoon:** Next attraction / market / activity + include approx travel time or distance
- **Evening:** Sunset spot / dinner / chill activity suggestion
- **Food Suggestions:** Mention 1 breakfast place, 1 lunch spot, 1 dinner spot (name only, no long description)

💰 Budget: total within ₹{int(budget * 83)}, per day ~₹{round((budget * 83) / days)}

🏨 Hotels: 3 best stays (name + location + approx ₹/night)
🍽️ Restaurants: 3 best local food spots (name + cuisine + must try dish)

💡 Travel Tips: exactly 3 bullet points
"""
                result = generate_fast(prompt)
            st.session_state["last_result"] = result
            st.session_state["last_inputs"] = {
                "country": country, "city": city, "days": int(days), "budget": int(budget),
                "travel_date": str(travel_date), "interests": interests
            }

    # Output
    if result:
        li = st.session_state["last_inputs"]
        st.success(f"✅ Travel Plan for {li['city']}, {li['country']} Ready!")
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown(result)
        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Plan"):
                tid = save_trip(user["id"], li["country"], li["city"], li["days"], li["budget"], li["travel_date"], li["interests"], result)
                st.success(f"Saved! Trip ID: {tid}")
        with col2:
            st.download_button(
                "📄 Download Full Trip Plan (PDF)",
                data=create_pdf(result),
                file_name=f"{li['city']}_AI_TravelPlan.pdf",
                mime="application/pdf"
            )

        # Map
        st.markdown('<div class="section-box"><h3>📍 Map View of Destination</h3>', unsafe_allow_html=True)
        try:
            df = pd.read_csv("worldcities.csv")
            df["city"] = df["city"].str.lower().str.strip()
            city_cleaned = li["city"].lower().strip()

            fallback = {
                "udupi": (13.3409,74.7421), "manipal": (13.3419,74.7558), "malpe": (13.3615,74.7033),
                "goa": (15.2993, 74.1240), "jaipur": (26.9124, 75.7873), "mumbai": (19.0760,72.8777)
            }
            row = df[df["city"]==city_cleaned]
            if not row.empty:
                lat,lon = float(row.iloc[0]["lat"]), float(row.iloc[0]["lng"])
                st.success(f"✅ {li['city'].title()} found: {lat}, {lon}")
            elif city_cleaned in fallback:
                lat,lon = fallback[city_cleaned]; st.info(f"ℹ️ Using fallback coordinates for {li['city'].title()}.")
            else:
                lat,lon = (20.5937,78.9629); st.warning("⚠️ City not in CSV. Showing India map.")

            city_df = pd.DataFrame([{"lat":lat,"lon":lon,"city":li["city"].title()}])
            st.pydeck_chart(pdk.Deck(
                initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=10),
                layers=[
                    pdk.Layer("ScatterplotLayer", city_df, get_position='[lon, lat]', get_radius=4000, get_color='[255,75,150,200]'),
                    pdk.Layer("TextLayer", city_df, get_position='[lon, lat]', get_text='city', get_size=24,
                              get_color='[255,255,255,255]', get_alignment_baseline='"bottom"')
                ]
            ))
        except Exception as e:
            st.error(f"⚠️ Map Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Recommendations (City + Budget)
        st.markdown("<div class='section-box'><h3>✨ Recommended Destinations for You</h3>", unsafe_allow_html=True)
        similar_places = {
            "goa": ["Gokarna","Pondicherry","Andaman","Varkala"],
            "manali": ["Kasol","Dharamshala","Shimla","Bir Billing"],
            "jaipur": ["Udaipur","Jodhpur","Jaisalmer","Agra"],
            "mumbai": ["Alibaug","Lonavala","Pune","Daman"],
            "bangalore": ["Mysore","Coorg","Ooty","Hampi"]
        }
        usd = li["budget"]
        if usd < 300: btag="Budget Friendly"
        elif usd <= 1200: btag="Mid Range"
        else: btag="Luxury"
        ckey = li["city"].lower()
        if ckey in similar_places:
            st.write(f"Since you planned **{li['city']}** and your budget is **{btag}**, you may also like:")
            for p in similar_places[ckey]:
                st.markdown(f"✅ **{p}** — similar travel vibe and cost range")
        else:
            st.info("No similar city recommendations found for this location yet. More cities can be added easily 😊")
        st.markdown("</div>", unsafe_allow_html=True)

    # Footer + Logout
    st.markdown("<hr>", unsafe_allow_html=True)
    c1,c2 = st.columns([3,1])
    with c1: st.markdown(f"<div class='footer-mini'>💜 {TITLE} | {TAGLINE}</div>", unsafe_allow_html=True)
    with c2:
        if st.button("🚪 Logout"):
            st.session_state.user=None
            st.experimental_rerun()

# -------------------- ROUTER --------------------
if st.session_state.user is None:
    auth_screen()
else:
    # header on main page
    st.markdown(f"<h1>🌎 {TITLE} ✈️</h1><div class='muted'>{TAGLINE}</div>", unsafe_allow_html=True)
    app_main()
