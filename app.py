# app.py  —  AI Travel Planner (Supabase PostgreSQL + psycopg2)

import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
from datetime import date, datetime
import pydeck as pdk
import pandas as pd
import hashlib
import json
import psycopg2
import psycopg2.extras

# -------------------- CONFIG --------------------
st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="wide")

TITLE = "AI TRAVEL PLANNER"
TAGLINE = "Plan smarter • Travel better • Powered by AI 💜"

# -------------------- STYLES --------------------
st.markdown("""
<style>
@keyframes pastelGradient {0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.stApp{
  background: linear-gradient(-45deg,#ece6ff,#f5e6ff,#ffe6fa,#e8faff);
  background-size:400% 400%; animation:pastelGradient 18s ease infinite;
  font-family:'Poppins',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
}
.hero-title{
  font-size:3.1rem;font-weight:900;text-align:center;
  background:linear-gradient(90deg,#6c00ff,#b43dee,#ff79c6);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.hero-tag{text-align:center;font-size:1.05rem;opacity:.9;margin-bottom:28px}
.glass-box{
  width:440px;max-width:94%;margin:auto;padding:24px;border-radius:18px;
  background:rgba(255,255,255,0.16);backdrop-filter:blur(14px);
  border:1px solid rgba(255,255,255,0.35);
  box-shadow:0 18px 60px rgba(31,38,135,0.35);
}
.section-box{
  background:rgba(255,255,255,0.78);
  padding:20px;border-radius:18px;margin-bottom:20px;
  box-shadow:0 0 20px rgba(150,120,255,0.25);
}
.muted{opacity:.85;font-size:.92rem;text-align:center}
div.stButton>button{
  background: linear-gradient(90deg,#a678f5,#c084fc,#d8b4fe); color:#fff; border:none; border-radius:12px;
  padding:.8rem 1.2rem; font-weight:600; box-shadow:0 0 20px rgba(180,120,255,.6); transition:.25s;
}
div.stButton>button:hover{ transform:scale(1.04); box-shadow:0 0 30px rgba(190,130,255,.85); }
</style>
""", unsafe_allow_html=True)

# -------------------- API KEY --------------------
try:
    API_KEY = st.secrets["general"]["GOOGLE_API_KEY"]
except Exception:
    st.error("🚫 Google API key missing. Add it in Secrets under [general] GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=API_KEY)

# -------------------- DB (Supabase PostgreSQL via psycopg2) --------------------
def get_conn():
    try:
        dsn = st.secrets["db"]["SUPABASE_URL"]
    except Exception:
        st.error("🚫 Database URL missing. Add it in Secrets under [db] SUPABASE_URL.")
        st.stop()
    # psycopg2 accepts DSN string; enforce SSL
    return psycopg2.connect(dsn, sslmode="require")

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                create table if not exists users(
                    id bigserial primary key,
                    name text,
                    email text unique,
                    password_hash text
                );
            """)
            cur.execute("""
                create table if not exists trips(
                    id bigserial primary key,
                    user_id bigint references users(id) on delete cascade,
                    country text,
                    city text,
                    days integer,
                    budget_usd integer,
                    travel_date text,
                    interests text,
                    result_text text,
                    created_at timestamp default now()
                );
            """)
            # seed demo user if not exists
            cur.execute("select id from users where email=%s", ("demo@example.com",))
            if not cur.fetchone():
                cur.execute(
                    "insert into users(name,email,password_hash) values(%s,%s,%s)",
                    ("Demo User","demo@example.com", hashlib.sha256("demo123".encode()).hexdigest())
                )
        conn.commit()

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def signup_user(name, email, password):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into users(name,email,password_hash) values(%s,%s,%s)",
                    (name, email, hash_pw(password))
                )
        return True, "Account created! Please log in."
    except psycopg2.Error as e:
        if getattr(e, "pgcode", ""):
            return False, "Email already registered or DB error."
        return False, "Could not create account."

def login_user(email, password):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("select id,name,password_hash from users where email=%s", (email,))
            row = cur.fetchone()
            if row and row["password_hash"] == hash_pw(password):
                return {"id": row["id"], "email": email, "name": row["name"] or ""}
    return None

def save_trip(user_id, inputs, result_text):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """insert into trips (user_id,country,city,days,budget_usd,travel_date,interests,result_text)
                   values (%s,%s,%s,%s,%s,%s,%s,%s) returning id""",
                (user_id, inputs["country"], inputs["city"], inputs["days"], inputs["budget"],
                 inputs["travel_date"], json.dumps(inputs["interests"]), result_text)
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id

def load_trips(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """select id,country,city,days,budget_usd,travel_date,interests,created_at
                   from trips where user_id=%s order by id desc""",
                (user_id,)
            )
            return cur.fetchall()

def load_trip_detail(trip_id, user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """select id,country,city,days,budget_usd,travel_date,interests,result_text,created_at
                   from trips where id=%s and user_id=%s""",
                (trip_id, user_id)
            )
            return cur.fetchone()

init_db()

# -------------------- AI + PDF --------------------
def generate_fast(prompt_text, model_name="models/gemini-2.5-flash"):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"[❌ Error: {e}]"

def create_pdf(text):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", size=14)
    for line in (text or "").split("\n"):
        safe = line.encode('latin-1','replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe)
    return BytesIO(pdf.output(dest="S").encode("latin-1"))

# -------------------- SESSION --------------------
if "user" not in st.session_state: st.session_state.user = None
if "last_result" not in st.session_state: st.session_state.last_result = ""
if "last_inputs" not in st.session_state: st.session_state.last_inputs = {}

# -------------------- AUTH (Glowing Hero) --------------------
def auth_screen():
    st.markdown(f"<div class='hero-title'>🌎 {TITLE} ✈️</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-tag'>{TAGLINE}</div>", unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔐 Login", "🆕 Sign Up"])

    with tab_login:
        st.markdown("<div class='glass-box'>", unsafe_allow_html=True)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("✨ Login", use_container_width=True):
            user = login_user(email, password)
            if user:
                st.session_state.user = user
                st.success("Logged in! Loading planner…")
                st.experimental_rerun()
            else:
                st.error("Invalid email or password.")
        st.caption("Try demo: demo@example.com / demo123")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_signup:
        st.markdown("<div class='glass-box'>", unsafe_allow_html=True)
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
                ok, msg = signup_user(name_su, email_su, pw_su)
                st.success(msg) if ok else st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)

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
            rows = []
            for r in trips:
                # id,country,city,days,budget,travel_date,interests,created_at
                rows.append({
                    "Trip ID": r[0], "Country": r[1], "City": r[2], "Days": r[3],
                    "Budget (USD)": r[4], "Start Date": r[5],
                    "Interests": ", ".join(json.loads(r[6] or "[]")),
                    "Created": str(r[7])[:19]
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
            selected_id = st.number_input("Enter Trip ID to open", min_value=0, step=1, value=0)
            if st.button("Open Saved Trip"):
                if selected_id:
                    d = load_trip_detail(selected_id, user["id"])
                    if d:
                        _, country, city, days, budget, tdate, interests_js, result_text, created = d
                        st.success(f"Opened Trip #{selected_id}: {city}, {country}")
                        with st.container(border=True):
                            st.markdown(result_text if result_text else "_No content saved_")
                            st.download_button(
                                "📄 Download Full Trip Plan (PDF)",
                                data=create_pdf(result_text or ""),
                                file_name=f"{city}_AI_TravelPlan.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.error("Trip not found or not yours.")

    # Inputs
    st.markdown("<div class='section-box'><h3>📝 Plan Your Trip</h3>", unsafe_allow_html=True)
    country = st.text_input("🌍 Country", value="India")
    city = st.text_input("🏙️ City", value="Goa")
    days = st.number_input("🗓️ Number of Days", 1, 15, 5)
    budget = st.number_input("💰 Budget (USD)", 100, 20000, 1500)
    travel_date = st.date_input("📅 Start Date", date.today())
    interests = st.multiselect("🎯 Interests", ["Nature", "Adventure", "Food", "Culture", "Beaches", "History", "Shopping"])
    st.markdown("</div>", unsafe_allow_html=True)

    result = st.session_state.get("last_result", "")

    # Generate (PROMPT KEPT EXACTLY AS YOU WROTE)
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
                tid = save_trip(st.session_state.user["id"], li, result)
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
    with c1: st.markdown(f"<div class='muted'>💜 {TITLE} | {TAGLINE}</div>", unsafe_allow_html=True)
    with c2:
        if st.button("🚪 Logout"):
            st.session_state.user=None
            st.experimental_rerun()

# -------------------- ROUTER --------------------
if st.session_state.user is None:
    auth_screen()   # LOGIN FIRST
else:
    st.markdown(f"<h1 class='hero-title'>🌎 {TITLE} ✈️</h1><div class='hero-tag'>{TAGLINE}</div>", unsafe_allow_html=True)
    app_main()
