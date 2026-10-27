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

CROP_PRICING = {
    "Mustard (सरसों)": {"msp": 5950, "glut": 5450, "smart": 6350},
    "Wheat (गेहूँ)": {"msp": 2275, "glut": 2100, "smart": 2500},
    "Potato (आलू)": {"msp": 1800, "glut": 1200, "smart": 2200},
    "Bajra (बाजरा)": {"msp": 2625, "glut": 2400, "smart": 2850},
    "Paddy / Rice (धान)": {"msp": 2300, "glut": 2150, "smart": 2550}
}

CROP_SCHEDULES = {
    "Mustard (सरसों)": [
        {"days": "0 - 10 दिन", "stage": "अंकुरण (Germination)", "task": "बीज अंकुरण की सघनता जांचें। प्रति वर्ग मीटर 45-60 पौधे होने चाहिए।"},
        {"days": "20 - 25 दिन", "stage": "निराई-गुड़ाई (Weeding & Thinning)", "task": "घने पौधों को हटाएं और पहली निराई करें।"},
        {"days": "30 - 35 दिन", "stage": "प्रथम सिंचाई व यूरिया (1st Irrigation & Urea)", "task": "हल्की सिंचाई करें। सिंचाई से ठीक पहले अनुशंसित यूरिया की आधी मात्रा दें।"},
        {"days": "45 - 55 दिन", "stage": "फूलत अवस्था (Flowering & Boron Spray)", "task": "फूल आने से ठीक पहले बोरॉन 20% (1.5 ग्राम/लीटर) का पर्ण स्प्रे करें। माहू (Aphid) कीट की निगरानी करें।"},
        {"days": "70 - 80 दिन", "stage": "फली भराव (Pod Filling)", "task": "दूसरी हल्की सिंचाई करें ताकि दाने भरते समय नमी बनी रहे।"},
        {"days": "110 - 120 दिन", "stage": "परिपक्वता व कटाई (Maturity & Harvest)", "task": "जब 75% फलियाँ भूरी हो जाएं, कटाई करें।"}
    ],
    "Wheat (गेहूँ)": [
        {"days": "0 - 10 दिन", "stage": "अंकुरण (Germination)", "task": "उचित नमी पर बुवाई सुनिश्चित करें। अंकुरण की निगरानी करें।"},
        {"days": "20 - 25 दिन", "stage": "ताज मूल अवस्था (CRI Stage)", "task": "पहली सिंचाई सीआरआई अवस्था पर अत्यंत आवश्यक है। इसके साथ नत्रता (यूरिया) दें।"},
        {"days": "40 - 45 दिन", "stage": "कले फूटना (Tillering)", "task": "दूसरी सिंचाई और खरपतवार नियंत्रण करें।"},
        {"days": "60 - 65 दिन", "stage": "गाँठ बन्ना व बालियाँ (Jointing & Heading)", "task": "तीसरी सिंचाई दें। नाइट्रोजन की शेष मात्रा का प्रयोग करें।"},
        {"days": "85 - 90 दिन", "stage": "दुग्धावस्था (Milking Stage)", "task": "चौथी सिंचाई। पीला रतुआ (Yellow Rust) रोग की जाँच करें।"},
        {"days": "120 - 130 दिन", "stage": "परिपक्वता (Harvesting)", "task": "दाने सख्त होने पर कटाई करें।"}
    ],
    "Potato (आलू)": [
        {"days": "0 - 15 दिन", "stage": "अंकुरण (Emergence)", "task": "कंदों का अंकुरण शुरू होता है। खेत में जलभराव न होने दें।"},
        {"days": "25 - 30 दिन", "stage": "मिट्टी चढ़ाना व पहली यूरिया (Earthing up)", "task": "पहली निराई-गुड़ाई करके पौधों पर मिट्टी चढ़ाएं और यूरिया दें।"},
        {"days": "45 - 50 दिन", "stage": "कंद विकास (Tuber Bulking)", "task": "दूसरी बार मिट्टी चढ़ाना, नियमित अंतराल पर सिंचाई करना। पिछेती झुलसा (Late Blight) पर नजर रखें।"},
        {"days": "75 - 90 दिन", "stage": "कन्द परिपक्वता (Maturity)", "task": "सिंचाई बंद कर दें ताकि छिलका सख्त हो जाए।"},
        {"days": "100 - 110 दिन", "stage": "बेल सुखाई व खदाई (Digging)", "task": "खोदाई से 10 दिन पहले बेल काट दें।"}
    ]
}

def init_databases():
    if not os.path.exists(LOGS_CSV):
        pd.DataFrame([{"Timestamp": "2026-10-10 09:00", "FarmerName": "Baseline", "Mobile": "-", "Village": "All", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Standard", "DAS": 0, "Growth_Stage": "Pre-Sowing", "Category": "Land Prep", "Input_Qty": "1", "Amount_INR": 20000.0, "CropCondition": "Healthy", "Notes": "Baseline"}]).to_csv(LOGS_CSV, index=False, encoding='utf-8-sig')

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
        return {
            "temp": curr.get("temperature_2m", 26.5),
            "rh": curr.get("relative_humidity_2m", 58),
            "wind": curr.get("wind_speed_10m", 8.5),
            "rain_3d": round(sum(daily.get("precipitation_sum", [0,0,0])[:3]), 1),
            "et0": round(daily.get("et0_fao_evapotranspiration", [3.2])[0], 2)
        }
    except Exception:
        return {"temp": 26.5, "rh": 60, "wind": 9.0, "rain_3d": 0.0, "et0": 3.4}

def extract_khatauni_info(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.lower().endswith(".pdf") and PdfReader is not None:
            reader = PdfReader(uploaded_file)
            for page in reader.pages: text += (page.extract_text() or "") + "\n"
        else:
            text = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception:
        pass
    ha_matches = re.findall(r"\b([0-4]?\d\.\d{3,4})\b", text)
    return float(ha_matches[0]) if ha_matches else None, 100, "Gata 101"

st.sidebar.title("🌾 Agri DSS किसान पोर्टल")
app_mode = st.sidebar.radio("📲 Select Mode:", ["📱 किसान मोबाइल ऐप (Farmer Easy Mode)", "🖥️ Full Admin & Research Dashboard"])

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Global Crop Pricing Benchmark")
selected_ref_crop = st.sidebar.selectbox("Select Crop:", list(CROP_PRICING.keys()))
ref_p = CROP_PRICING[selected_ref_crop]
smart_hold_base = st.sidebar.number_input("60-Day Smart Price (₹/Q)", value=ref_p["smart"], step=50)
storage_cost_q = st.sidebar.number_input("Storage Cost (₹/Q)", value=90, step=10)

total_area_kb = df['SubPlotKB'].sum() if 'SubPlotKB' in df.columns else 34.0
total_incurred = logs_df['Amount_INR'].sum()
grand_total_cop = total_incurred + 360.0 * total_area_kb

df['Pred_Total_Yield_Q'] = (2.05 * df['SubPlotKB']).round(2)
df['Total_CoP_INR'] = ((df['SubPlotKB'] / total_area_kb) * grand_total_cop).round(0)
df['Rev_SmartMarket_INR'] = (df['Pred_Total_Yield_Q'] * (smart_hold_base - storage_cost_q)).round(0)
df['Net_Profit_Smart_INR'] = df['Rev_SmartMarket_INR'] - df['Total_CoP_INR']

if app_mode == "📱 किसान मोबाइल ऐप (Farmer Easy Mode)":
    st.title("🌾 किसान मित्र (Farmer Support App)")
    st.caption("स्मार्ट निर्णय सहायता प्रणाली - पूर्ण कृषि सलाह एवं समय-सारणी")

    if "logged_in_mobile" not in st.session_state:
        st.session_state.logged_in_mobile = None

    if st.session_state.logged_in_mobile is None:
        st.markdown("### 🔐 कृपया लॉगिन करें या नया पंजीकरण करें (Login or Register)")
        tab_login, tab_reg = st.tabs(["🔑 किसान लॉगिन (Login)", "➕ नया किसान पंजीकरण (Register)"])

        with tab_login:
            with st.form("login_form"):
                mob_input = st.text_input("📱 मोबाइल नंबर या अंतिम 4 अंक दर्ज करें:", placeholder="उदा: 1122 या 3344")
                if st.form_submit_button("🚀 लॉगिन करें") and mob_input:
                    match = df[df['Mobile'].str.contains(mob_input.strip(), case=False, na=False)]
                    if len(match) > 0:
                        st.session_state.logged_in_mobile = mob_input.strip()
                        st.success("✅ लॉगिन सफल!")
                        st.rerun()
                    else:
                        st.error("❌ नंबर नहीं मिला। डेमो के लिए `1122` या `3344` डालें।")

        with tab_reg:
            uploaded_khatauni = st.file_uploader("📄 खतौनी फ़ाइल (PDF/TXT - Optional)", type=["pdf", "txt"])
            auto_ha = 0.3372
            if uploaded_khatauni is not None:
                ext_ha, _, _ = extract_khatauni_info(uploaded_khatauni)
                if ext_ha: auto_ha = round(ext_ha, 4)

            calc_ha = st.number_input("📐 क्षेत्रफल (Hectare):", value=float(auto_ha), format="%.4f")
            calc_kb = round(calc_ha / 0.0843, 1)

            with st.form("quick_reg_form"):
                r_name = st.text_input("किसान का नाम*")
                r_mob = st.text_input("मोबाइल नंबर (10 अंक)*", placeholder="9837001122")
                r_vill = st.selectbox("गाँव चुनें*", list(VILLAGE_COORDS.keys()))
                r_crop = st.selectbox("उगाई जाने वाली फसल (Crop)*", list(CROP_PRICING.keys()))
                r_khata = st.number_input("खतौनी संख्या", value=142)
                r_gata = st.text_input("गाटा संख्या", value="Gata 218")
                if st.form_submit_button("🌾 रजिस्टर करें और लॉगिन करें") and r_name and r_mob:
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

    m_tab1, m_tab2 = st.tabs(["📱 1. मेरी खेत सलाह, मौसम व समय-सारणी (My Plot Advisory & Schedule)", "📸 2. पौधों की गिनती व खर्च (Stand Count & Log)"])

    with m_tab1:
        sel_sub = st.selectbox("📍 अपना खेत / सब-प्लॉट चुनें:", farmer_df['SubPlotID'].unique())
        r = farmer_df[farmer_df['SubPlotID'] == sel_sub].iloc[0]
        wx = fetch_live_weather(float(r['Latitude']), float(r['Longitude']))
        crop_name = r['Present_Crop']

        try:
            sowing_dt = datetime.strptime(str(r['Sowing_Date']).split()[0], "%Y-%m-%d")
            das = (datetime.now() - sowing_dt).days
        except Exception:
            das = 12

        st.markdown(f"#### 🌾 चयनित फसल: **{crop_name}** | बुवाई तिथि: {r['Sowing_Date']} (बुवाई से दिन: **{das} DAS**)")
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("🌡️ तापमान", f"{wx['temp']} °C")
        w2.metric("💧 नमी", f"{wx['rh']} %")
        w3.metric("🌧️ 3-दिन बारिश", f"{wx['rain_3d']} mm")
        w4.metric("💨 हवा", f"{wx['wind']} km/h")

        if wx['rain_3d'] >= 5:
            st.info(f"🌧️ **मौसम अलर्ट:** अगले 3 दिन **{wx['rain_3d']} mm** बारिश की संभावना है। सिंचाई रोकें!")

        st.markdown(f"""
        <div style="background-color:#f1f8e9; padding:20px; border-radius:12px; border:3px solid #2e7d32; margin-top:10px; color:#111111;">
            <h3 style="color:#1b5e20; margin-top:0;">🌾 किसान सलाह और आर्थिक पासबुक ({farmer_name})</h3>
            <p style="font-size:16px; color:#111111;"><b>गाँव / खसरा:</b> {r['Village']} (Khatauni: {r['KhatauniNo']}) | <b>प्लॉट:</b> {r['SubPlotID']} ({r['Elevation']}) | <b>क्षेत्रफल:</b> {r['SubPlotKB']} कच्चा बीघा</p>
            <p style="font-size:15px; color:#111111;"><b>वर्तमान फसल:</b> {crop_name} ({r['Seed_Variety']}) | <b>मिट्टी pH:</b> {r['pH']} | <b>बोरॉन:</b> {r.get('B', 0.5)} ppm</p>
            <hr style="border:1px solid #81c784;">
            <h4 style="color:#b71c1c; margin-bottom:6px;">📅 इस खेत के लिए महत्वपूर्ण कृषि सलाह:</h4>
            <ol style="font-size:15.5px; line-height:1.6; color:#111111;">
                <li><b>उर्वरक संस्तुति ({r['SubPlotKB']} KB हेतु):</b> यूरिया: <b>{r['Rec_Urea_kg']} kg</b> | SSP: <b>{r['Rec_SSP_kg']} kg</b> | पोटाश: <b>{r['Rec_MOP_kg']} kg</b> | जिप्सम: <b>{r['Rec_Gypsum_kg']} kg</b></li>
                <li><b>सिंचाई प्रबंधन:</b> फसल की अवस्था अनुसार हल्की सिंचाई करें। जलभराव से बचाव करें।</li>
                <li><b>रोग व कीट नियंत्रण:</b> मौसम में नमी अधिक होने पर माहू या फंगस की नियमित निगरानी करें और संस्तुत जैविक/रासायनिक सुरक्षा अपनाएं।</li>
            </ol>
            <hr style="border:1px solid #81c784;">
            <p style="font-size:16px; color:#1b5e20;"><b>💰 कुल लागत:</b> ₹{r['Total_CoP_INR']:,.0f} | <b>अपेक्षित पैदावार:</b> {r['Pred_Total_Yield_Q']} क्विंटल | <b>शुद्ध लाभ:</b> ₹{r['Net_Profit_Smart_INR']:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"### 🗓️ फसल की चरण-दर-चरण समय-सारणी (Crop Growth Schedule for {crop_name})")
        
        matched_sched_key = next((k for k in CROP_SCHEDULES.keys() if k.split()[0] in crop_name), "Mustard (सरसों)")
        sched_list = CROP_SCHEDULES[matched_sched_key]

        for item in sched_list:
            st.markdown(f"""
            <div style="background-color:#ffffff; padding:12px 18px; border-radius:8px; border-left:5px solid #2e7d32; margin-bottom:8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <span style="background-color:#e8f5e9; color:#2e7d32; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:14px;">⏱️ {item['days']}</span>
                <b style="color:#1b5e20; font-size:16px; margin-left:10px;">{item['stage']}</b>
                <p style="margin:6px 0 0 0; color:#333; font-size:15px;">👉 {item['task']}</p>
            </div>
            """, unsafe_allow_html=True)

    with m_tab2:
        st.subheader("📸 फसल की स्थिति, पौधों की गिनती (Stand Count) व खर्च दर्ज करें")
        st.caption("यहाँ आप अंकुरण के बाद पौधों की गिनती (Plant Count/m²), फसल की स्थिति, फोटो और सिंचाई/खाद के खर्च दर्ज कर सकते हैं।")

        log_plot = st.selectbox("📍 किस खेत/प्लॉट का डेटा दर्ज करना है?", farmer_df['SubPlotID'].unique(), key="log_plot_select")
        plot_row = farmer_df[farmer_df['SubPlotID'] == log_plot].iloc[0]

        try:
            p_sowing = datetime.strptime(str(plot_row['Sowing_Date']).split()[0], "%Y-%m-%d")
            plot_das = (datetime.now() - p_sowing).days
        except Exception:
            plot_das = 12

        with st.form("comprehensive_field_log_form", clear_on_submit=False):
            col_l1, col_l2 = st.columns(2)

            with col_l1:
                log_type = st.radio(
                    "📝 क्या दर्ज करना चाहते हैं? (Select Entry Type):",
                    ["🌱 पौधों की गिनती (Stand Count per m²)", "💰 सिंचाई व कृषि आदान खर्च (Expense)", "📸 दोनों / अन्य गतिविधि (Both/General)"],
                    horizontal=True
                )

                st.markdown("---")
                st.markdown("##### 🌱 अंकुरण व पौधों की गिनती (Stand Count Audit)")
                stand_count = st.number_input(
                    "1x1 मीटर घेरे में पौधों की संख्या (Plants / m²):",
                    min_value=0,
                    max_value=250,
                    value=52 if "गिनती" in log_type or "दोनों" in log_type else 0,
                    step=1,
                    help="खेत में 1x1 मीटर का फ्रेम डालकर गिने गए पौधों की औसत संख्या दर्ज करें।"
                )

                crop_condition = st.selectbox(
                    "🌿 फसल की सामान्य स्थिति (Crop Condition):",
                    [
                        "Healthy (स्वस्थ अंकुरण)",
                        "Under-Populated / Patchy (बिरल / कहीं-कहीं खाली)",
                        "Over-Crowded (बहुत घना - छटनी योग्य)",
                        "Leaf Yellowing (पत्ते पीले पड़ना)",
                        "Pest / Aphids (कीट / माहू का प्रकोप)",
                        "Moisture Stress (नमी की कमी / मुरझाना)"
                    ]
                )

            with col_l2:
                st.markdown("##### 💰 खर्च व कृषि कार्य (यदि कोई हो)")
                f_cat = st.selectbox(
                    "गतिविधि / खर्च का प्रकार (Category):",
                    [
                        "Stand Count Audit (अंकुरण व पौधों की गिनती)",
                        "Irrigation (सिंचाई)",
                        "Fertiliser (खाद/यूरिया)",
                        "Thinning / Weeding (छटनी व निराई)",
                        "Weedicide/Pesticide Spray (दवा स्प्रे)",
                        "Harvesting (कटाई)",
                        "Other (अन्य)"
                    ]
                )

                f_amt = st.number_input(
                    "खर्च की राशि ₹ (Amount Incurred - यदि कोई खर्च न हो तो 0 रखें):",
                    min_value=0.0,
                    value=0.0 if "गिनती" in log_type else 500.0,
                    step=50.0
                )

                f_notes = st.text_input(
                    "📝 अतिरिक्त टिप्पणी (Notes):",
                    placeholder="उदा: 3 स्थानों पर औसत 54 पौधे/m² मिले, अंकुरण एक समान है।"
                )

                camera_photo = st.camera_input("📷 फोन कैमरे से खेत/पौधों की फोटो लें (Optional)")

            submit_log = st.form_submit_button("💾 डेटा सुरक्षित करें (Save Event)")

            if submit_log:
                stand_feedback = ""
                if stand_count > 0:
                    if stand_count < 30:
                        stand_feedback = f"⚠️ **बिरल अंकुरण ({stand_count} पौधे/m²):** पौधों की संख्या कम है। जहाँ खाली पैच हैं वहाँ तुरंत बीज रोपाई (Gap Filling) करें।"
                    elif 40 <= stand_count <= 65:
                        stand_feedback = f"🎯 **सर्वोत्तम जमाव ({stand_count} पौधे/m²):** पौधों की सघनता आदर्श है। कोई छटनी की आवश्यकता नहीं है।"
                    elif stand_count > 70:
                        stand_feedback = f"🌿 **सघन अंकुरण ({stand_count} पौधे/m²):** फसल काफी घनी है। 20-25 दिन की अवस्था पर छटनी (Thinning) करके 10-12 सेमी की दूरी बनाएं।"

                combined_notes = f"Stand: {stand_count} plants/m2. {f_notes}".strip()

                new_l = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "FarmerName": farmer_name,
                    "Mobile": logged_val,
                    "Village": plot_row['Village'],
                    "SubPlotID": log_plot,
                    "Present_Crop": plot_row['Present_Crop'],
                    "Seed_Variety": plot_row['Seed_Variety'],
                    "DAS": plot_das,
                    "Growth_Stage": "10-DAS Emergence" if stand_count > 0 else "Vegetative",
                    "Category": f_cat,
                    "Input_Qty": f"{stand_count} plants/m2" if stand_count > 0 else "1",
                    "Amount_INR": f_amt,
                    "CropCondition": crop_condition,
                    "Notes": combined_notes
                }])
                pd.concat([logs_df, new_l], ignore_index=True).to_csv(LOGS_CSV, index=False, encoding='utf-8-sig')
                st.success(f"✅ खेत **{log_plot}** का डेटा सफलतापूर्वक दर्ज हो गया!")
                if stand_feedback:
                    st.info(stand_feedback)

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
