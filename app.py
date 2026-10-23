# ==============================================================================
# AGRI DSS: PERMANENT MULTIMODAL MOBILE & RESEARCH PLATFORM (38-COLUMN SCHEMA)
# ==============================================================================
import os
import glob
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Agri DSS | किसान मित्र पोर्टल",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

MASTER_CSV = "Agri_DSS_Live.csv.csv"
LOGS_CSV = "farmer_field_logs_v2.csv"

# ------------------------------------------------------------------------------
# 2. SELF-HEALING DATABASE INITIALIZER
# ------------------------------------------------------------------------------
def init_databases():
    if not os.path.exists(MASTER_CSV):
        # Fallback default master data
        default_data = [
            {'FarmCode': 'NC', 'FarmerName': 'Praveen Kumar', 'Village': 'Nagla Chatura (नगला चतुर)', 'KhatauniNo': 142, 'KhasraGata': 'Gata 218Ka, 218Kha, 219', 'KhatauniHa': 1.0117, 'TotalKachhaBigha': 12, 'SubPlotID': 'NCH', 'Elevation': 'HIGH', 'SubPlotKB': 4.0, 'pH': 8.11, 'EC': 0.95, 'OC': 0.40, 'N': 75.6, 'P': 18, 'K': 213, 'S': 12.57, 'Zn': 0.69, 'B': 0.76, 'Fe': 4.97, 'Mn': 3.83, 'Cu': 0.43, 'Rec_Urea_kg': 73.3, 'Rec_SSP_kg': 84.3, 'Rec_MOP_kg': 14.1, 'Rec_Gypsum_kg': 42.2, 'Rec_Borax_kg': 0.0, 'Mobile': '98XXXXXXXX', 'Soil_Texture': 'Loamy (दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Pioneer 45S46', 'Sowing_Date': '2026-10-15', 'Irrigation_Source': 'Submersible Tube-well', 'Prev_Season_Crop': 'Bajra (बाजरा - Kharif)', 'Prev_Yield_Q': 7.2, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed for Fodder', 'Prev_Disease_History': 'None'},
            {'FarmCode': 'MLP', 'FarmerName': 'K Srinivas', 'Village': 'Malupur (मालूपुर)', 'KhatauniNo': 89, 'KhasraGata': 'Gata 104/2', 'KhatauniHa': 0.3372, 'TotalKachhaBigha': 4, 'SubPlotID': 'MLP-H', 'Elevation': 'HIGH', 'SubPlotKB': 2.0, 'pH': 7.15, 'EC': 0.748, 'OC': 0.21, 'N': 68.67, 'P': 16, 'K': 101, 'S': 12.36, 'Zn': 0.79, 'B': 0.39, 'Fe': 5.40, 'Mn': 3.84, 'Cu': 0.31, 'Rec_Urea_kg': 36.7, 'Rec_SSP_kg': 42.2, 'Rec_MOP_kg': 14.1, 'Rec_Gypsum_kg': 12.6, 'Rec_Borax_kg': 1.69, 'Mobile': '98XXXXXXXX', 'Soil_Texture': 'Sandy Loam (बलुई दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Local Improved', 'Sowing_Date': '2026-10-18', 'Irrigation_Source': 'Canal & Tube-well', 'Prev_Season_Crop': 'Moong / Fallow (मूंग / खाली)', 'Prev_Yield_Q': 2.0, 'Prev_Irrigation_Count': 1, 'Prev_Residue_Mgmt': 'Ploughed in Soil', 'Prev_Disease_History': 'None'},
            {'FarmCode': 'DS', 'FarmerName': 'K Srinivas', 'Village': 'Dera Sapra (डेरा सपरा)', 'KhatauniNo': 215, 'KhasraGata': 'Gata 311, 312', 'KhatauniHa': 0.5059, 'TotalKachhaBigha': 6, 'SubPlotID': 'DS-H', 'Elevation': 'HIGH', 'SubPlotKB': 3.0, 'pH': 8.04, 'EC': 0.766, 'OC': 0.39, 'N': 70.56, 'P': 22, 'K': 146, 'S': 12.57, 'Zn': 0.88, 'B': 0.59, 'Fe': 4.35, 'Mn': 3.01, 'Cu': 0.32, 'Rec_Urea_kg': 46.7, 'Rec_SSP_kg': 63.2, 'Rec_MOP_kg': 16.9, 'Rec_Gypsum_kg': 31.6, 'Rec_Borax_kg': 0.0, 'Mobile': '98XXXXXXXX', 'Soil_Texture': 'Loamy (दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'RH-725', 'Sowing_Date': '2026-10-16', 'Irrigation_Source': 'Tube-well', 'Prev_Season_Crop': 'Bajra (बाजरा - Kharif)', 'Prev_Yield_Q': 5.1, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed for Fodder', 'Prev_Disease_History': 'None'},
            {'FarmCode': 'MP', 'FarmerName': 'K Srinivas', 'Village': 'Madanpur (मदनपुर)', 'KhatauniNo': 176, 'KhasraGata': 'Gata 405, 406/1', 'KhatauniHa': 1.0117, 'TotalKachhaBigha': 12, 'SubPlotID': 'MP-H', 'Elevation': 'HIGH', 'SubPlotKB': 6.0, 'pH': 8.16, 'EC': 0.768, 'OC': 0.24, 'N': 76.23, 'P': 25, 'K': 101, 'S': 13.09, 'Zn': 0.82, 'B': 0.52, 'Fe': 6.24, 'Mn': 3.06, 'Cu': 0.37, 'Rec_Urea_kg': 93.5, 'Rec_SSP_kg': 101.2, 'Rec_MOP_kg': 42.2, 'Rec_Gypsum_kg': 126.5, 'Rec_Borax_kg': 2.53, 'Mobile': '98XXXXXXXX', 'Soil_Texture': 'Sandy Alkaline (रेतीली क्षारीय)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Local Hardie', 'Sowing_Date': '2026-10-20', 'Irrigation_Source': 'Tube-well (Brackish)', 'Prev_Season_Crop': 'Fallow (खाली खेत)', 'Prev_Yield_Q': 0.0, 'Prev_Irrigation_Count': 0, 'Prev_Residue_Mgmt': 'Mulched', 'Prev_Disease_History': 'None'}
        ]
        pd.DataFrame(default_data).to_csv(MASTER_CSV, index=False)

    if not os.path.exists(LOGS_CSV):
        init_logs = [
            {"Timestamp": "2026-10-10 09:00", "FarmerName": "Baseline", "Mobile": "-", "Village": "All", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Standard", "DAS": 5, "Growth_Stage": "Germination", "Category": "Land Preparation", "Input_Qty": "1 Cultivator", "Amount_INR": 20000.0, "CropCondition": "Healthy", "Notes": "Land prep across 34 KB"},
            {"Timestamp": "2026-10-12 11:30", "FarmerName": "Baseline", "Mobile": "-", "Village": "All", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Standard", "DAS": 7, "Growth_Stage": "Germination", "Category": "Fertiliser Procurement", "Input_Qty": "Basal Dose", "Amount_INR": 21480.0, "CropCondition": "Healthy", "Notes": "NPK & Sulphur procurement"}
        ]
        pd.DataFrame(init_logs).to_csv(LOGS_CSV, index=False)

init_databases()
df = pd.read_csv(MASTER_CSV)
logs_df = pd.read_csv(LOGS_CSV)

# ------------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# ------------------------------------------------------------------------------
st.sidebar.title("🌾 Agri DSS किसान पोर्टल")
app_mode = st.sidebar.radio(
    "📲 Select Interface Mode / मोड चुनें:",
    ["📱 किसान मोबाइल ऐप (Farmer Easy Mode)", "🖥️ Full Admin & Research Dashboard"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Market Pricing (₹ / Quintal)")
msp_price = st.sidebar.number_input("Govt MSP Price", value=5950, step=50)
glut_price = st.sidebar.number_input("Harvest Glut Mandi Price", value=5450, step=50)
smart_hold_base = st.sidebar.number_input("60-Day Smart Price", value=6350, step=50)
storage_cost_q = st.sidebar.number_input("Storage Cost", value=90, step=10)

# ------------------------------------------------------------------------------
# 4. BIO-ECONOMIC & COST MODEL
# ------------------------------------------------------------------------------
total_area_kb = df['SubPlotKB'].sum() if 'SubPlotKB' in df.columns else 34.0
total_incurred = logs_df['Amount_INR'].sum()

logged_irrigation = logs_df[logs_df['Category'].str.contains("Irrigation", na=False)]['Amount_INR'].sum()
logged_weedicide = logs_df[logs_df['Category'].str.contains("Weedicide|Spray", na=False)]['Amount_INR'].sum()
logged_harvest = logs_df[logs_df['Category'].str.contains("Harvest", na=False)]['Amount_INR'].sum()

rem_irrigation = max(0.0, (360.0 * total_area_kb) - logged_irrigation)
rem_weedicide = max(0.0, (140.0 * total_area_kb) - logged_weedicide)
rem_harvest = max(0.0, (480.0 * total_area_kb) - logged_harvest)

grand_total_cop = total_incurred + rem_irrigation + rem_weedicide + rem_harvest

base_yield_map = {'NCH': 2.10, 'NCM': 2.02, 'NCL': 2.12, 'MLP-H': 1.98, 'MLP-L': 2.25, 'DS-H': 2.15, 'DS-L': 2.10, 'MP-H': 1.88, 'MP-L': 1.82}
df['Pred_Total_Yield_Q'] = (df['SubPlotID'].map(base_yield_map).fillna(2.05) * df['SubPlotKB']).round(2)
df['Total_CoP_INR'] = ((df['SubPlotKB'] / total_area_kb) * grand_total_cop).round(0)
df['Rev_SmartMarket_INR'] = (df['Pred_Total_Yield_Q'] * (smart_hold_base - storage_cost_q)).round(0)
df['Net_Profit_Smart_INR'] = df['Rev_SmartMarket_INR'] - df['Total_CoP_INR']

# ==============================================================================
# MODE 1: FARMER MOBILE VIEW
# ==============================================================================
if app_mode == "📱 किसान मोबाइल ऐप (Farmer Easy Mode)":
    st.title("🌾 किसान मित्र (Farmer Support App)")
    st.caption("सरसों और रबी फसलों के लिए स्मार्ट निर्णय सहायता प्रणाली")

    m_tab1, m_tab2, m_tab3 = st.tabs([
        "📱 1. मेरी खेत सलाह (My Plot Advisory)",
        "📸 2. सिंचाई, खर्च व फसल फोटो (Log Event)",
        "➕ 3. नया किसान पंजीकरण (New Farmer Join)"
    ])

    with m_tab1:
        sel_sub = st.selectbox("📍 अपना खेत / सब-प्लॉट चुनें:", df['SubPlotID'].unique())
        r = df[df['SubPlotID'] == sel_sub].iloc[0]

        st.markdown(f"""
        <div style="background-color:#f1f8e9; padding:20px; border-radius:12px; border:3px solid #2e7d32;">
            <h3 style="color:#1b5e20; margin-top:0;">🌾 किसान सलाह और आर्थिक पासबुक</h3>
            <p style="font-size:16px;"><b>गाँव / खसरा:</b> {r['Village']} (Khatauni: {r['KhatauniNo']}) | <b>प्लॉट:</b> {r['SubPlotID']} ({r['Elevation']}) | <b>क्षेत्रफल:</b> {r['SubPlotKB']} कच्चा बीघा</p>
            <p style="font-size:15px;"><b>वर्तमान फसल:</b> {r['Present_Crop']} ({r['Seed_Variety']}) | <b>मिट्टी pH:</b> {r['pH']} | <b>बोरॉन:</b> {r['B']} ppm</p>
            <hr style="border:1px solid #81c784;">
            <h4 style="color:#b71c1c; margin-bottom:6px;">📅 अगले 40 दिनों का ज़रूरी कार्य:</h4>
            <ol style="font-size:15.5px; line-height:1.6;">
                <li><b>अंकुरण जांच (10 दिन):</b> 1x1 मीटर घेरे में पौधों की गिनती करें (45–60 पौधे)।</li>
                <li><b>सिंचाई और यूरिया:</b> {'<b>⚠️ रेतीली मिट्टी (22–25 दिन पर):</b> पहली सिंचाई हल्की करें। पानी से 1 घंटा पहले <b>18 किलो यूरिया + ह्यूमिक एसिड</b> डालें।' if 'MP' in str(r['FarmCode']) else '<b>30–35 दिन पर:</b> पहली सिंचाई से ठीक पहले यूरिया की टॉप-ड्रेसिंग करें।'}</li>
                <li><b>बोरॉन स्प्रे (38–42 दिन):</b> {'इस खेत में बोरॉन की कमी (' + str(r['B']) + ' ppm) है। फूल आने से पहले <b>इफको बोरॉन 20% (1.5 ग्राम/लीटर)</b> का स्प्रे करें।' if r['B']<0.5 else 'फसल वृद्धि के लिए जैव-उत्प्रेरक का स्प्रे करें।'}</li>
            </ol>
            <hr style="border:1px solid #81c784;">
            <p style="font-size:16px; color:#1b5e20;"><b>💰 कुल लागत:</b> ₹{r['Total_CoP_INR']:,.0f} | <b>अनुमानित पैदावार:</b> {r['Pred_Total_Yield_Q']} क्विंटल | <b>शुद्ध लाभ:</b> ₹{r['Net_Profit_Smart_INR']:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with m_tab2:
        st.subheader("📸 फसल की फोटो और सिंचाई / खर्च दर्ज करें")
        with st.form("mobile_update_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("किसान का नाम (Farmer Name)")
                f_plot = st.selectbox("प्लॉट चुनें", ["ALL (सभी खेत)"] + list(df['SubPlotID'].unique()))
                f_cat = st.selectbox("खर्च का प्रकार", ["Irrigation (सिंचाई)", "Fertiliser (खाद/यूरिया)", "Weedicide/Spray (स्प्रे)", "Harvesting (कटाई)"])
                f_amt = st.number_input("खर्च की राशि ₹", min_value=0.0, value=0.0, step=100.0)
            with c2:
                f_cond = st.selectbox("फसल की स्थिति", ["Normal / स्वस्थ", "Leaf Yellowing / पत्ते पीले पड़ना", "Pest / कीट या माहू", "Wilting / नमी की कमी"])
                cam_photo = st.camera_input("📷 फोन कैमरे से फोटो लें (Optional)")
                f_notes = st.text_input("टिप्पणी", placeholder="जैसे: पहली सिंचाई पूरी हुई")

            sub_btn = st.form_submit_button("💾 सेव करें और सलाह पाएं")
            if sub_btn:
                new_log = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "FarmerName": f_name if f_name else "Farmer",
                    "Mobile": "-", "Village": "Local", "SubPlotID": f_plot.split(" ")[0],
                    "Present_Crop": "Mustard", "Seed_Variety": "Pioneer", "DAS": 30, "Growth_Stage": "Vegetative",
                    "Category": f_cat, "Input_Qty": "1", "Amount_INR": f_amt, "CropCondition": f_cond, "Notes": f_notes
                }])
                pd.concat([logs_df, new_log], ignore_index=True).to_csv(LOGS_CSV, index=False)
                st.success(f"✅ डेटा सेव हो गया! खर्च: ₹{f_amt:,.0f}")
                if "Yellowing" in f_cond:
                    st.warning("🚨 **सलाह:** नाइट्रोजन/सल्फर की कमी हो सकती है। यूरिया + ह्यूमिक एसिड दें और NPK 19:19:19 का स्प्रे करें।")

    with m_tab3:
        st.subheader("➕ नया किसान और पिछली फसल का इतिहास जोड़ें")
        with st.form("new_farmer_form", clear_on_submit=True):
            nf1, nf2 = st.columns(2)
            with nf1:
                nf_name = st.text_input("किसान का नाम")
                nf_village = st.text_input("गाँव का नाम")
                nf_kb = st.number_input("खेत का क्षेत्रफल (कच्चा बीघा)", value=4.0)
                nf_soil = st.selectbox("मिट्टी का प्रकार", ["दोमट मिट्टी (Loamy)", "रेतीली / क्षारीय (Sandy Alkaline)"])
            with nf2:
                prev_crop = st.selectbox("पिछले सीजन में कौन सी फसल थी?", ["Bajra (बाजरा)", "Fallow (खाली)", "Moong / ढैंचा (दलहन)", "Paddy (धान)"])
                prev_yield = st.number_input("पिछली पैदावार (क्विंटल)", value=6.0)
                prev_irrig = st.number_input("पिछली सिंचाई संख्या", value=2)

            nf_submit = st.form_submit_button("🌾 रजिस्टर करें")
            if nf_submit and nf_name:
                new_id = f"{nf_village[:3].upper()}-{len(df)+1}"
                proxy = {"pH": 8.1, "EC": 0.5, "OC": 0.45, "N": 210, "P": 18, "K": 160, "S": 12, "Zn": 0.8, "B": 0.45, "Fe": 5.0, "Mn": 3.8, "Cu": 0.4, "Rec_Urea_kg": 50.0, "Rec_SSP_kg": 60.0, "Rec_MOP_kg": 15.0, "Rec_Gypsum_kg": 30.0, "Rec_Borax_kg": 1.5}
                new_row = pd.DataFrame([{
                    "SubPlotID": new_id, "Village": f"{nf_village} ({nf_name})", "FarmCode": "NEW",
                    "KhatauniNo": 0, "KhasraGata": "New", "KhatauniHa": 0.1, "TotalKachhaBigha": nf_kb,
                    "Elevation": "MEDIUM", "SubPlotKB": nf_kb, **proxy,
                    "Mobile": "98XXXXXXXX", "Soil_Texture": nf_soil,
                    "Present_Crop": "Mustard (सरसों)", "Seed_Variety": "Standard", "Sowing_Date": "2026-10-15", "Irrigation_Source": "Tube-well",
                    "Prev_Season_Crop": prev_crop, "Prev_Yield_Q": prev_yield, "Prev_Irrigation_Count": prev_irrig,
                    "Prev_Residue_Mgmt": "Removed", "Prev_Disease_History": "None"
                }])
                pd.concat([df, new_row], ignore_index=True).to_csv(MASTER_CSV, index=False)
                st.success(f"🎉 खेत कोड **{new_id}** सफलतापूर्वक जुड़ गया है!")

# ==============================================================================
# MODE 2: ADMIN & RESEARCH DASHBOARD
# ==============================================================================
else:
    st.title("🌾 Agri DSS: Admin & Research Dashboard (38-Column Master)")
    tab1, tab2, tab3 = st.tabs(["💰 Expense Audit", "🧪 Soil & Previous Season Training Data", "🗄️ Excel Admin Editor"])
    
    with tab1:
        st.subheader("Ground-Truth Cost Breakdown")
        st.metric("Total Incurred Cost", f"₹{total_incurred:,.0f}", f"₹{grand_total_cop/total_area_kb:,.0f} / KB")
        st.dataframe(logs_df, use_container_width=True)

    with tab2:
        st.subheader("Complete 38-Column Master Database (Including Training History)")
        st.dataframe(df, use_container_width=True)

    with tab3:
        st.subheader("🗄️ Spreadsheet Admin Editor")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Changes"):
            edited_df.to_csv(MASTER_CSV, index=False)
            st.success("✅ Master Database Saved Successfully!")
            st.rerun()
