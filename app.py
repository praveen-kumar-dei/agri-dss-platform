import os
import re
import requests
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

st.set_page_config(
    page_title="Agri DSS | किसान मित्र पोर्टल",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

MASTER_CSV = "Agri_DSS_Live.csv"
LOGS_CSV = "farmer_field_logs_v2.csv"
ADMIN_PIN = "2026"

VILLAGE_COORDS = {
    "Nagla Chatura (नगला चतुर)": {"lat": 27.3212, "lon": 78.0845, "code": "NC", "soil": "Loamy (दोमट)"},
    "Malupur (मालूपुर)": {"lat": 27.3338, "lon": 78.0918, "code": "MLP", "soil": "Sandy Loam (बलुई दोमट)"},
    "Dera Sapra (डेरा सपरा)": {"lat": 27.3088, "lon": 78.1052, "code": "DS", "soil": "Loamy (दोमट)"},
    "Madanpur (मदनपुर)": {"lat": 27.2978, "lon": 78.1182, "code": "MP", "soil": "Sandy Alkaline (रेतीली क्षारीय)"},
    "Other Village (अन्य गाँव - खंदौली/एत्मादपुर)": {"lat": 27.3150, "lon": 78.0950, "code": "AGR", "soil": "Loamy (दोमट)"}
}

# Crop Pricing Benchmark Dictionary (₹ per Quintal)
CROP_PRICING = {
    "Mustard (सरसों)": {"msp": 5950, "glut": 5450, "smart": 6350},
    "Wheat (गेहूँ)": {"msp": 2275, "glut": 2100, "smart": 2500},
    "Potato (आलू)": {"msp": 1800, "glut": 1200, "smart": 2200},
    "Bajra (बाजरा)": {"msp": 2625, "glut": 2400, "smart": 2850},
    "Paddy / Rice (धान)": {"msp": 2300, "glut": 2150, "smart": 2550}
}

def init_databases():
    if not os.path.exists(LOGS_CSV):
        init_logs = [
            {"Timestamp": "2026-10-10 09:00", "FarmerName": "Baseline", "Mobile": "-", "Village": "All 4 Villages", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Pioneer 45S46", "DAS": 0, "Growth_Stage": "Pre-Sowing", "Category": "Land Preparation", "Input_Qty": "Cultivator & Leveling", "Amount_INR": 20000.0, "CropCondition": "Normal / स्वस्थ", "Notes": "Land prep across 34 KB"}
        ]
        pd.DataFrame(init_logs).to_csv(LOGS_CSV, index=False, encoding='utf-8-sig')

init_databases()
df = pd.read_csv(MASTER_CSV)
logs_df = pd.read_csv(LOGS_CSV)
df['Mobile'] = df['Mobile'].astype(str)

@st.cache_data(ttl=1800)
def fetch_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration&timezone=Asia%2FKolkata&forecast_days=5"
        res = requests.get(url, timeout=5).json()
        curr = res.get("current", {})
        daily = res.get("daily", {})
        rain_3d = sum(daily.get("precipitation_sum", [0, 0, 0])[:3])
        et0_today = daily.get("et0_fao_evapotranspiration", [3.2])[0]
        return {"temp": curr.get("temperature_2m", 26.5), "rh": curr.get("relative_humidity_2m", 58), "wind": curr.get("wind_speed_10m", 8.5), "rain_3d": round(rain_3d, 1), "et0": round(et0_today, 2)}
    except Exception:
        return {"temp": 26.5, "rh": 60, "wind": 9.0, "rain_3d": 0.0, "et0": 3.4}

def extract_khatauni_info(uploaded_file):
    text = ""
    fname = uploaded_file.name.lower()
    try:
        if fname.endswith(".pdf") and PdfReader is not None:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        elif fname.endswith((".txt", ".csv", ".html", ".htm")):
            text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception:
        pass
    ha_matches = re.findall(r"\b([0-4]?\d\.\d{3,4})\b", text)
    extracted_ha = float(ha_matches[0]) if ha_matches else None
    khatauni_matches = re.findall(r"(?:खाता|खतौनी|Khatauni)\s*[:\-]?\s*0*(\d{1,5})", text, re.IGNORECASE)
    extracted_khatauni = int(khatauni_matches[0]) if khatauni_matches else None
    gata_matches = re.findall(r"(?:खसरा|गाटा|Gata)\s*[:\-]?\s*([0-9A-Za-z/,\s]+)", text, re.IGNORECASE)
    extracted_gata = gata_matches[0].strip()[:25] if gata_matches else None
    return extracted_ha, extracted_khatauni, extracted_gata

st.sidebar.title("🌾 Agri DSS किसान पोर्टल")
app_mode = st.sidebar.radio(
    "📲 Select Interface Mode / मोड चुनें:",
    ["📱 किसान मोबाइल ऐप (Farmer Easy Mode)", "🖥️ Full Admin & Research Dashboard"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Global Crop Pricing Benchmark")
selected_ref_crop = st.sidebar.selectbox("Select Benchmark Crop:", list(CROP_PRICING.keys()))
ref_p = CROP_PRICING[selected_ref_crop]

msp_price = st.sidebar.number_input("Govt MSP (₹/Q)", value=ref_p["msp"], step=50)
glut_price = st.sidebar.number_input("Harvest Glut Mandi (₹/Q)", value=ref_p["glut"], step=50)
smart_hold_base = st.sidebar.number_input("60-Day Smart Price (₹/Q)", value=ref_p["smart"], step=50)
storage_cost_q = st.sidebar.number_input("Storage Cost (₹/Q)", value=90, step=10)

total_area_kb = df['SubPlotKB'].sum() if 'SubPlotKB' in df.columns else 34.0
total_incurred = logs_df['Amount_INR'].sum()
grand_total_cop = total_incurred + 360.0 * total_area_kb

base_yield_map = {'NCH': 2.10, 'NCM': 2.02, 'NCL': 2.12, 'MLP-H': 1.98, 'MLP-L': 2.25, 'DS-H': 2.15, 'DS-L': 2.10, 'MP-H': 1.88, 'MP-L': 1.82}
df['Pred_Total_Yield_Q'] = (df['SubPlotID'].map(base_yield_map).fillna(2.05) * df['SubPlotKB']).round(2)
df['Total_CoP_INR'] = ((df['SubPlotKB'] / total_area_kb) * grand_total_cop).round(0)
df['Rev_SmartMarket_INR'] = (df['Pred_Total_Yield_Q'] * (smart_hold_base - storage_cost_q)).round(0)
df['Net_Profit_Smart_INR'] = df['Rev_SmartMarket_INR'] - df['Total_CoP_INR']

if app_mode == "📱 किसान मोबाइल ऐप (Farmer Easy Mode)":
    st.title("🌾 किसान मित्र (Farmer Support App)")
    st.caption("स्मार्ट निर्णय सहायता प्रणाली - फसल विशिष्ट बाज़ार मूल्य और सलाह")

    if "logged_in_mobile" not in st.session_state:
        st.session_state.logged_in_mobile = None

    if st.session_state.logged_in_mobile is None:
        st.markdown("### 🔐 कृपया लॉगिन करें या नया पंजीकरण करें (Login or Register)")
        tab_login, tab_reg = st.tabs(["🔑 किसान लॉगिन (Login)", "➕ नया किसान पंजीकरण (Register)"])

        with tab_login:
            with st.form("login_form"):
                mob_input = st.text_input("📱 मोबाइल नंबर या अंतिम 4 अंक दर्ज करें:", placeholder="उदा: 1122 या 3344")
                login_btn = st.form_submit_button("🚀 लॉगिन करें (Login)")
                if login_btn and mob_input:
                    match = df[df['Mobile'].str.contains(mob_input.strip(), case=False, na=False)]
                    if len(match) > 0:
                        st.session_state.logged_in_mobile = mob_input.strip()
                        st.success("✅ लॉगिन सफल!")
                        st.rerun()
                    else:
                        st.error("❌ नंबर नहीं मिला। डेमो के लिए `1122` या `3344` डालें।")

        with tab_reg:
            st.markdown("##### 📄 स्टेप 1 (वैकल्पिक): अपनी खतौनी अपलोड करें")
            uploaded_khatauni = st.file_uploader("📄 खतौनी फ़ाइल (PDF/TXT)", type=["pdf", "txt", "html"])
            auto_ha, auto_kno, auto_gata = 0.3372, 100, "Gata 101"
            if uploaded_khatauni is not None:
                ext_ha, ext_kno, ext_gata = extract_khatauni_info(uploaded_khatauni)
                if ext_ha: auto_ha = round(ext_ha, 4)
                if ext_kno: auto_kno = ext_kno
                if ext_gata: auto_gata = ext_gata

            calc_ha = st.number_input("📐 क्षेत्रफल (Hectare):", value=float(auto_ha), format="%.4f")
            calc_kb = round(calc_ha / 0.0843, 1)
            st.info(f"🔄 कुल कच्चा बीघा: **{calc_kb} KB**")

            with st.form("quick_reg_form"):
                r_name = st.text_input("किसान का नाम*")
                r_mob = st.text_input("मोबाइल नंबर (10 अंक)*", placeholder="9837001122")
                r_vill = st.selectbox("गाँव चुनें*", list(VILLAGE_COORDS.keys()))
                r_crop = st.selectbox("उगाई जाने वाली फसल (Select Crop)*", list(CROP_PRICING.keys()))
                r_khata = st.number_input("खतौनी संख्या", value=int(auto_kno))
                r_gata = st.text_input("गाटा संख्या", value=auto_gata)
                r_submit = st.form_submit_button("🌾 रजिस्टर करें और लॉगिन करें")
                if r_submit and r_name and r_mob:
                    v_inf = VILLAGE_COORDS[r_vill]
                    new_id = f"{v_inf['code']}-{len(df)+1}"
                    proxy = {"pH": 8.1, "EC": 0.65, "OC": 0.40, "N": 74.0, "P": 19, "K": 155, "S": 12.5, "Zn": 0.85, "B": 0.48, "Fe": 5.4, "Mn": 3.8, "Cu": 0.40, "Rec_Urea_kg": round(18.3*calc_kb,1), "Rec_SSP_kg": round(21.0*calc_kb,1), "Rec_MOP_kg": round(5.5*calc_kb,1), "Rec_Gypsum_kg": round(10.5*calc_kb,1), "Rec_Borax_kg": round(0.84*calc_kb,2)}
                    new_row = pd.DataFrame([{
                        "FarmCode": v_inf['code'], "FarmerName": r_name, "Village": r_vill, "KhatauniNo": int(r_khata), "KhasraGata": r_gata, "KhatauniHa": calc_ha, "TotalKachhaBigha": calc_kb, "SubPlotID": new_id, "Elevation": "MEDIUM", "SubPlotKB": calc_kb, **proxy, "Mobile": r_mob.strip(), "Soil_Texture": v_inf['soil'], "Present_Crop": r_crop, "Seed_Variety": "Certified Local", "Sowing_Date": datetime.now().strftime("%Y-%m-%d"), "Irrigation_Source": "Tube-well", "Prev_Season_Crop": "Fallow", "Prev_Yield_Q": 5.0, "Prev_Irrigation_Count": 2, "Prev_Residue_Mgmt": "Removed", "Prev_Disease_History": "None", "Latitude": v_inf['lat'], "Longitude": v_inf['lon']
                    }])
                    pd.concat([df, new_row], ignore_index=True).to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')
                    st.session_state.logged_in_mobile = r_mob.strip()[-4:]
                    st.success("🎉 पंजीकरण सफल! ऑटो-लॉगिन हो रहा है...")
                    st.rerun()
        st.stop()

    # --- LOGGED IN FARMER VIEW ---
    logged_val = st.session_state.logged_in_mobile
    farmer_df = df[df['Mobile'].str.contains(logged_val, case=False, na=False)]
    farmer_name = farmer_df['FarmerName'].iloc[0] if len(farmer_df) > 0 else "Farmer"

    col_top1, col_top2 = st.columns([4, 1])
    with col_top1:
        st.success(f"👤 **लॉगिन:** {farmer_name} | कुल सब-प्लॉट: {len(farmer_df)}")
    with col_top2:
        if st.button("🚪 लॉग आउट"):
            st.session_state.logged_in_mobile = None
            st.rerun()

    m_tab1, m_tab2 = st.tabs(["📱 1. मेरी खेत सलाह व फसल मूल्य (My Plot & Crop Pricing)", "📸 2. सिंचाई व खर्च दर्ज करें (Log Event)"])

    with m_tab1:
        sel_sub = st.selectbox("📍 अपना खेत / सब-प्लॉट चुनें:", farmer_df['SubPlotID'].unique())
        r = farmer_df[farmer_df['SubPlotID'] == sel_sub].iloc[0]
        wx = fetch_live_weather(float(r['Latitude']), float(r['Longitude']))
        crop_name = r['Present_Crop']

        st.markdown(f"#### 🌾 चयनित फसल: **{crop_name}** ({r['Village']})")
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("🌡️ तापमान", f"{wx['temp']} °C")
        w2.metric("💧 नमी", f"{wx['rh']} %")
        w3.metric("🌧️ 3-दिन बारिश", f"{wx['rain_3d']} mm")
        w4.metric("💨 हवा", f"{wx['wind']} km/h")

        st.markdown(f"""
        <div style="background-color:#f1f8e9; padding:20px; border-radius:12px; border:3px solid #2e7d32;">
            <h3 style="color:#1b5e20; margin-top:0;">🌱 फसल विवरण एवं आर्थिक पासबुक ({crop_name})</h3>
            <p><b>प्लॉट ID:</b> {r['SubPlotID']} | <b>खतौनी:</b> {r['KhatauniNo']} | <b>क्षेत्रफल:</b> {r['SubPlotKB']} कच्चा बीघा</p>
            <p><b>मिट्टी pH:</b> {r['pH']} | <b>बोरॉन:</b> {r['B']} ppm | <b>बीज किस्म:</b> {r['Seed_Variety']}</p>
            <hr style="border:1px solid #81c784;">
            <h4>📅 संस्तुत खाद मात्रा:</h4>
            <ul>
                <li>यूरिया: <b>{r['Rec_Urea_kg']} kg</b></li>
                <li>SSP: <b>{r['Rec_SSP_kg']} kg</b></li>
                <li>MOP (पोटाश): <b>{r['Rec_MOP_kg']} kg</b></li>
                <li>जिप्सम: <b>{r['Rec_Gypsum_kg']} kg</b></li>
            </ul>
            <p><b>💰 अनुमानित कुल लागत:</b> ₹{r['Total_CoP_INR']:,.0f} | <b>अपेक्षित पैदावार:</b> {r['Pred_Total_Yield_Q']} क्विंटल | <b>शुद्ध लाभ ({crop_name}):</b> ₹{r['Net_Profit_Smart_INR']:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with m_tab2:
        with st.form("log_form", clear_on_submit=True):
            f_cat = st.selectbox("खर्च का प्रकार", ["Irrigation (सिंचाई)", "Fertiliser (खाद)", "Weedicide/Spray (स्प्रे)"])
            f_amt = st.number_input("राशि ₹", min_value=0.0, value=500.0)
            f_notes = st.text_input("टिप्पणी")
            if st.form_submit_button("💾 सेव करें"):
                new_l = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "FarmerName": farmer_name, "Mobile": logged_val, "Village": r['Village'], "SubPlotID": sel_sub, "Present_Crop": r['Present_Crop'], "Seed_Variety": r['Seed_Variety'], "DAS": 30, "Growth_Stage": "Vegetative", "Category": f_cat, "Input_Qty": "1", "Amount_INR": f_amt, "CropCondition": "Healthy", "Notes": f_notes}])
                pd.concat([logs_df, new_l], ignore_index=True).to_csv(LOGS_CSV, index=False, encoding='utf-8-sig')
                st.success("✅ खर्च दर्ज हो गया!")

else:
    st.title("🌾 Agri DSS: Admin & Research Dashboard")
    pin = st.sidebar.text_input("🔒 Admin PIN:", type="password", placeholder="PIN: 2026")
    if pin != ADMIN_PIN:
        st.warning("🔒 कृपया एडमिन पिन (`2026`) दर्ज करें।")
        st.stop()
    st.sidebar.success("🔓 Unlocked")
    tab1, tab2 = st.tabs(["🧪 40-Column Master Data", "🗄️ Spreadsheet Editor"])
    with tab1: st.dataframe(df)
    with tab2:
        ed = st.data_editor(df, num_rows="dynamic")
        if st.button("💾 Save"):
            ed.to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')
            st.success("Saved!")
            st.rerun()
