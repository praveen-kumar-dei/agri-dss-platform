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

# Village GPS & Soil Proxy Fallbacks (Etmadpur / Khandauli, Agra)
VILLAGE_COORDS = {
    "Nagla Chatura (नगला चतुर)": {"lat": 27.3212, "lon": 78.0845, "code": "NC", "soil": "Loamy (दोमट)"},
    "Malupur (मालूपुर)": {"lat": 27.3338, "lon": 78.0918, "code": "MLP", "soil": "Sandy Loam (बलुई दोमट)"},
    "Dera Sapra (डेरा सपरा)": {"lat": 27.3088, "lon": 78.1052, "code": "DS", "soil": "Loamy (दोमट)"},
    "Madanpur (मदनपुर)": {"lat": 27.2978, "lon": 78.1182, "code": "MP", "soil": "Sandy Alkaline (रेतीली क्षारीय)"},
    "Other Village (अन्य गाँव - खंदौली/एत्मादपुर)": {"lat": 27.3150, "lon": 78.0950, "code": "AGR", "soil": "Loamy (दोमट)"}
}

def init_databases():
    default_data = [
        {'FarmCode': 'NC', 'FarmerName': 'Praveen Kumar', 'Village': 'Nagla Chatura (नगला चतुर)', 'KhatauniNo': 142, 'KhasraGata': 'Gata 218Ka, 218Kha, 219', 'KhatauniHa': 1.0117, 'TotalKachhaBigha': 12, 'SubPlotID': 'NCH', 'Elevation': 'HIGH', 'SubPlotKB': 3.0, 'pH': 8.11, 'EC': 0.95, 'OC': 0.40, 'N': 75.6, 'P': 18, 'K': 213, 'S': 12.57, 'Zn': 0.69, 'B': 0.76, 'Fe': 4.97, 'Mn': 3.83, 'Cu': 0.43, 'Rec_Urea_kg': 55.0, 'Rec_SSP_kg': 63.2, 'Rec_MOP_kg': 10.5, 'Rec_Gypsum_kg': 31.6, 'Rec_Borax_kg': 0.0, 'Mobile': '9837001122', 'Soil_Texture': 'Loamy (दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Pioneer 45S46', 'Sowing_Date': '2026-10-15', 'Irrigation_Source': 'Submersible Tube-well', 'Prev_Season_Crop': 'Bajra (बाजरा - Kharif)', 'Prev_Yield_Q': 5.4, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed for Fodder', 'Prev_Disease_History': 'None', 'Latitude': 27.3215, 'Longitude': 78.0842},
        {'FarmCode': 'NC', 'FarmerName': 'K Srinivas', 'Village': 'Nagla Chatura (नगला चतुर)', 'KhatauniNo': 142, 'KhasraGata': 'Gata 218Ka, 218Kha, 219', 'KhatauniHa': 1.0117, 'TotalKachhaBigha': 12, 'SubPlotID': 'NCM', 'Elevation': 'MEDIUM', 'SubPlotKB': 6.0, 'pH': 8.35, 'EC': 0.735, 'OC': 0.36, 'N': 69.93, 'P': 20, 'K': 235, 'S': 13.09, 'Zn': 0.88, 'B': 0.49, 'Fe': 5.32, 'Mn': 4.80, 'Cu': 0.38, 'Rec_Urea_kg': 110.0, 'Rec_SSP_kg': 126.5, 'Rec_MOP_kg': 21.0, 'Rec_Gypsum_kg': 126.5, 'Rec_Borax_kg': 5.06, 'Mobile': '9837003344', 'Soil_Texture': 'Loamy (दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Giriraj', 'Sowing_Date': '2026-10-16', 'Irrigation_Source': 'Submersible Tube-well', 'Prev_Season_Crop': 'Bajra (बाजरा - Kharif)', 'Prev_Yield_Q': 10.5, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed for Fodder', 'Prev_Disease_History': 'None', 'Latitude': 27.3210, 'Longitude': 78.0848},
        {'FarmCode': 'NC', 'FarmerName': 'K Srinivas', 'Village': 'Nagla Chatura (नगला चतुर)', 'KhatauniNo': 142, 'KhasraGata': 'Gata 218Ka, 218Kha, 219', 'KhatauniHa': 1.0117, 'TotalKachhaBigha': 12, 'SubPlotID': 'NCL', 'Elevation': 'LOW', 'SubPlotKB': 3.0, 'pH': 8.14, 'EC': 0.642, 'OC': 0.31, 'N': 72.45, 'P': 25, 'K': 146, 'S': 11.48, 'Zn': 0.99, 'B': 0.59, 'Fe': 6.36, 'Mn': 3.40, 'Cu': 0.47, 'Rec_Urea_kg': 55.0, 'Rec_SSP_kg': 50.5, 'Rec_MOP_kg': 16.9, 'Rec_Gypsum_kg': 31.6, 'Rec_Borax_kg': 0.0, 'Mobile': '9837003344', 'Soil_Texture': 'Loamy (दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Pioneer 45S46', 'Sowing_Date': '2026-10-15', 'Irrigation_Source': 'Submersible Tube-well', 'Prev_Season_Crop': 'Bajra (बाजरा - Kharif)', 'Prev_Yield_Q': 5.6, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed for Fodder', 'Prev_Disease_History': 'None', 'Latitude': 27.3205, 'Longitude': 78.0852},
        {'FarmCode': 'MLP', 'FarmerName': 'K Srinivas', 'Village': 'Malupur (मालूपुर)', 'KhatauniNo': 89, 'KhasraGata': 'Gata 104/2', 'KhatauniHa': 0.3372, 'TotalKachhaBigha': 4, 'SubPlotID': 'MLP-H', 'Elevation': 'HIGH', 'SubPlotKB': 2.0, 'pH': 7.15, 'EC': 0.748, 'OC': 0.21, 'N': 68.67, 'P': 16, 'K': 101, 'S': 12.36, 'Zn': 0.79, 'B': 0.39, 'Fe': 5.40, 'Mn': 3.84, 'Cu': 0.31, 'Rec_Urea_kg': 36.7, 'Rec_SSP_kg': 42.2, 'Rec_MOP_kg': 14.1, 'Rec_Gypsum_kg': 12.6, 'Rec_Borax_kg': 1.69, 'Mobile': '9837003344', 'Soil_Texture': 'Sandy Loam (बलुई दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Local Improved', 'Sowing_Date': '2026-10-18', 'Irrigation_Source': 'Canal & Tube-well', 'Prev_Season_Crop': 'Moong / Fallow (मूंग / खाली)', 'Prev_Yield_Q': 2.0, 'Prev_Irrigation_Count': 1, 'Prev_Residue_Mgmt': 'Ploughed in Soil', 'Prev_Disease_History': 'None', 'Latitude': 27.3340, 'Longitude': 78.0915},
        {'FarmCode': 'MLP', 'FarmerName': 'Praveen Kumar', 'Village': 'Malupur (मालूपुर)', 'KhatauniNo': 89, 'KhasraGata': 'Gata 104/2', 'KhatauniHa': 0.3372, 'TotalKachhaBigha': 4, 'SubPlotID': 'MLP-L', 'Elevation': 'LOW', 'SubPlotKB': 2.0, 'pH': 7.00, 'EC': 0.963, 'OC': 0.43, 'N': 74.34, 'P': 18, 'K': 121, 'S': 14.00, 'Zn': 0.91, 'B': 0.52, 'Fe': 6.93, 'Mn': 4.41, 'Cu': 0.42, 'Rec_Urea_kg': 36.7, 'Rec_SSP_kg': 42.2, 'Rec_MOP_kg': 11.2, 'Rec_Gypsum_kg': 12.6, 'Rec_Borax_kg': 0.84, 'Mobile': '9837001122', 'Soil_Texture': 'Sandy Loam (बलुई दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Pioneer 45S46', 'Sowing_Date': '2026-10-17', 'Irrigation_Source': 'Canal & Tube-well', 'Prev_Season_Crop': 'Moong / Fallow (मूंग / खाली)', 'Prev_Yield_Q': 2.2, 'Prev_Irrigation_Count': 1, 'Prev_Residue_Mgmt': 'Ploughed in Soil', 'Prev_Disease_History': 'None', 'Latitude': 27.3335, 'Longitude': 78.0920},
        {'FarmCode': 'DS', 'FarmerName': 'K Srinivas', 'Village': 'Dera Sapra (डेरा सपरा)', 'KhatauniNo': 215, 'KhasraGata': 'Gata 311, 312', 'KhatauniHa': 0.5059, 'TotalKachhaBigha': 6, 'SubPlotID': 'DS-H', 'Elevation': 'HIGH', 'SubPlotKB': 3.0, 'pH': 8.04, 'EC': 0.766, 'OC': 0.39, 'N': 70.56, 'P': 22, 'K': 146, 'S': 12.57, 'Zn': 0.88, 'B': 0.59, 'Fe': 4.35, 'Mn': 3.01, 'Cu': 0.32, 'Rec_Urea_kg': 46.7, 'Rec_SSP_kg': 63.2, 'Rec_MOP_kg': 16.9, 'Rec_Gypsum_kg': 31.6, 'Rec_Borax_kg': 0.0, 'Mobile': '9837003344', 'Soil_Texture': 'Loamy (दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'RH-725', 'Sowing_Date': '2026-10-16', 'Irrigation_Source': 'Tube-well', 'Prev_Season_Crop': 'Bajra (बाजरा - Kharif)', 'Prev_Yield_Q': 5.1, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed for Fodder', 'Prev_Disease_History': 'None', 'Latitude': 27.3090, 'Longitude': 78.1050},
        {'FarmCode': 'DS', 'FarmerName': 'K Srinivas', 'Village': 'Dera Sapra (डेरा सपरा)', 'KhatauniNo': 215, 'KhasraGata': 'Gata 311, 312', 'KhatauniHa': 0.5059, 'TotalKachhaBigha': 6, 'SubPlotID': 'DS-L', 'Elevation': 'LOW', 'SubPlotKB': 3.0, 'pH': 8.17, 'EC': 0.634, 'OC': 0.45, 'N': 81.27, 'P': 20, 'K': 146, 'S': 11.65, 'Zn': 0.96, 'B': 0.49, 'Fe': 5.96, 'Mn': 4.16, 'Cu': 0.45, 'Rec_Urea_kg': 46.7, 'Rec_SSP_kg': 63.2, 'Rec_MOP_kg': 16.9, 'Rec_Gypsum_kg': 31.6, 'Rec_Borax_kg': 2.53, 'Mobile': '9837003344', 'Soil_Texture': 'Loamy (दोमट)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'RH-725', 'Sowing_Date': '2026-10-16', 'Irrigation_Source': 'Tube-well', 'Prev_Season_Crop': 'Bajra (बाजरा - Kharif)', 'Prev_Yield_Q': 5.4, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed for Fodder', 'Prev_Disease_History': 'None', 'Latitude': 27.3085, 'Longitude': 78.1055},
        {'FarmCode': 'MP', 'FarmerName': 'K Srinivas', 'Village': 'Madanpur (मदनपुर)', 'KhatauniNo': 176, 'KhasraGata': 'Gata 405, 406/1', 'KhatauniHa': 1.0117, 'TotalKachhaBigha': 12, 'SubPlotID': 'MP-H', 'Elevation': 'HIGH', 'SubPlotKB': 6.0, 'pH': 8.16, 'EC': 0.768, 'OC': 0.24, 'N': 76.23, 'P': 25, 'K': 101, 'S': 13.09, 'Zn': 0.82, 'B': 0.52, 'Fe': 6.24, 'Mn': 3.06, 'Cu': 0.37, 'Rec_Urea_kg': 93.5, 'Rec_SSP_kg': 101.2, 'Rec_MOP_kg': 42.2, 'Rec_Gypsum_kg': 126.5, 'Rec_Borax_kg': 2.53, 'Mobile': '9837003344', 'Soil_Texture': 'Sandy Alkaline (रेतीली क्षारीय)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Local Hardie', 'Sowing_Date': '2026-10-20', 'Irrigation_Source': 'Tube-well (Brackish)', 'Prev_Season_Crop': 'Fallow (खाली खेत)', 'Prev_Yield_Q': 0.0, 'Prev_Irrigation_Count': 0, 'Prev_Residue_Mgmt': 'Mulched', 'Prev_Disease_History': 'None', 'Latitude': 27.2980, 'Longitude': 78.1180},
        {'FarmCode': 'MP', 'FarmerName': 'K Srinivas', 'Village': 'Madanpur (मदनपुर)', 'KhatauniNo': 176, 'KhasraGata': 'Gata 405, 406/1', 'KhatauniHa': 1.0117, 'TotalKachhaBigha': 12, 'SubPlotID': 'MP-L', 'Elevation': 'LOW', 'SubPlotKB': 6.0, 'pH': 8.51, 'EC': 0.569, 'OC': 0.46, 'N': 71.19, 'P': 18, 'K': 168, 'S': 11.48, 'Zn': 0.92, 'B': 0.39, 'Fe': 5.92, 'Mn': 4.01, 'Cu': 0.41, 'Rec_Urea_kg': 93.5, 'Rec_SSP_kg': 126.5, 'Rec_MOP_kg': 33.7, 'Rec_Gypsum_kg': 126.5, 'Rec_Borax_kg': 5.06, 'Mobile': '9837003344', 'Soil_Texture': 'Sandy Alkaline (रेतीली क्षारीय)', 'Present_Crop': 'Mustard (सरसों - Rabi)', 'Seed_Variety': 'Local Hardie', 'Sowing_Date': '2026-10-20', 'Irrigation_Source': 'Tube-well (Brackish)', 'Prev_Season_Crop': 'Fallow (खाली खेत)', 'Prev_Yield_Q': 0.0, 'Prev_Irrigation_Count': 0, 'Prev_Residue_Mgmt': 'Mulched', 'Prev_Disease_History': 'None', 'Latitude': 27.2975, 'Longitude': 78.1185}
    ]
    if not os.path.exists(MASTER_CSV):
        pd.DataFrame(default_data).to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')

    if not os.path.exists(LOGS_CSV):
        init_logs = [
            {"Timestamp": "2026-10-10 09:00", "FarmerName": "Baseline", "Mobile": "-", "Village": "All 4 Villages", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Pioneer 45S46", "DAS": 0, "Growth_Stage": "Pre-Sowing", "Category": "Land Preparation", "Input_Qty": "Cultivator & Leveling", "Amount_INR": 20000.0, "CropCondition": "Normal / स्वस्थ", "Notes": "Land prep across 34 KB"},
            {"Timestamp": "2026-10-12 11:30", "FarmerName": "Baseline", "Mobile": "-", "Village": "All 4 Villages", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Pioneer 45S46", "DAS": 0, "Growth_Stage": "Pre-Sowing", "Category": "Fertiliser Procurement", "Input_Qty": "Basal NPK & S", "Amount_INR": 21480.0, "CropCondition": "Normal / स्वस्थ", "Notes": "Basal fertilizer stock"},
            {"Timestamp": "2026-10-14 08:15", "FarmerName": "Baseline", "Mobile": "-", "Village": "All 4 Villages", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Pioneer 45S46", "DAS": 0, "Growth_Stage": "Sowing", "Category": "Seeds", "Input_Qty": "Certified Seed", "Amount_INR": 1500.0, "CropCondition": "Normal / स्वस्थ", "Notes": "Mustard seed procurement"},
            {"Timestamp": "2026-10-15 16:00", "FarmerName": "Baseline", "Mobile": "-", "Village": "All 4 Villages", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Pioneer 45S46", "DAS": 1, "Growth_Stage": "Germination", "Category": "Basal Application + Seeding", "Input_Qty": "Seeding Drill", "Amount_INR": 5460.0, "CropCondition": "Normal / स्वस्थ", "Notes": "Seeding completed"}
        ]
        pd.DataFrame(init_logs).to_csv(LOGS_CSV, index=False, encoding='utf-8-sig')

init_databases()
df = pd.read_csv(MASTER_CSV)
logs_df = pd.read_csv(LOGS_CSV)

# Self-healing check for Latitude, Longitude, and distinct Mobile numbers if an older CSV was cached
if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
    lat_map = {'NCH': 27.3215, 'NCM': 27.3210, 'NCL': 27.3205, 'MLP-H': 27.3340, 'MLP-L': 27.3335, 'DS-H': 27.3090, 'DS-L': 27.3085, 'MP-H': 27.2980, 'MP-L': 27.2975}
    lon_map = {'NCH': 78.0842, 'NCM': 78.0848, 'NCL': 78.0852, 'MLP-H': 78.0915, 'MLP-L': 78.0920, 'DS-H': 78.1050, 'DS-L': 78.1055, 'MP-H': 78.1180, 'MP-L': 78.1185}
    df['Latitude'] = df['SubPlotID'].map(lat_map).fillna(27.3150)
    df['Longitude'] = df['SubPlotID'].map(lon_map).fillna(78.0950)
    df.to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')

df['Mobile'] = df['Mobile'].astype(str)
if (df['Mobile'] == '98XXXXXXXX').any():
    df.loc[df['FarmerName'].str.contains('Praveen', case=False, na=False), 'Mobile'] = '9837001122'
    df.loc[df['FarmerName'].str.contains('Srinivas', case=False, na=False), 'Mobile'] = '9837003344'
    df.to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')

# ------------------------------------------------------------------------------
# HELPER 1: LIVE OPEN-METEO AGRICULTURAL WEATHER API
# ------------------------------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_live_weather(lat, lon):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration"
            "&timezone=Asia%2FKolkata&forecast_days=5"
        )
        res = requests.get(url, timeout=5).json()
        curr = res.get("current", {})
        daily = res.get("daily", {})
        rain_3d = sum(daily.get("precipitation_sum", [0, 0, 0])[:3])
        et0_today = daily.get("et0_fao_evapotranspiration", [3.2])[0]
        return {
            "temp": curr.get("temperature_2m", 26.5),
            "rh": curr.get("relative_humidity_2m", 58),
            "wind": curr.get("wind_speed_10m", 8.5),
            "rain_3d": round(rain_3d, 1),
            "et0": round(et0_today, 2),
            "status": "Live Satellite & Weather Station Feed"
        }
    except Exception:
        return {"temp": 26.5, "rh": 60, "wind": 9.0, "rain_3d": 0.0, "et0": 3.4, "status": "Regional Offline Baseline"}

# ------------------------------------------------------------------------------
# HELPER 2: KHATAUNI DOCUMENT EXTRACTOR (HECTARES -> KACHHA BIGHA)
# ------------------------------------------------------------------------------
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

    # Look for 4-decimal Hectare values typical of UP Bhulekh (e.g., 1.0117, 0.3372, 0.5059)
    ha_matches = re.findall(r"\b([0-4]?\d\.\d{3,4})\b", text)
    extracted_ha = float(ha_matches[0]) if ha_matches else None

    # Look for Khatauni number (3 to 5 digits)
    khatauni_matches = re.findall(r"(?:खाता|खतौनी|Khatauni|Khata)\s*[:\-]?\s*0*(\d{1,5})", text, re.IGNORECASE)
    extracted_khatauni = int(khatauni_matches[0]) if khatauni_matches else None

    # Look for Khasra / Gata number
    gata_matches = re.findall(r"(?:खसरा|गाटा|Gata|Khasra)\s*[:\-]?\s*([0-9A-Za-z/,\s]+)", text, re.IGNORECASE)
    extracted_gata = gata_matches[0].strip()[:25] if gata_matches else None

    return extracted_ha, extracted_khatauni, extracted_gata, len(text)

# ------------------------------------------------------------------------------
# SIDEBAR CONTROLS
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
# BIO-ECONOMIC & COST MODEL
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
# MODE 1: FARMER MOBILE VIEW (WITH PERSONALIZED LOGIN, KHATAUNI OCR & GPS MAP)
# ==============================================================================
if app_mode == "📱 किसान मोबाइल ऐप (Farmer Easy Mode)":
    st.title("🌾 किसान मित्र (Farmer Support App)")
    st.caption("सरसों और रबी फसलों के लिए स्मार्ट निर्णय सहायता प्रणाली (Agra Region)")

    m_tab1, m_tab2, m_tab3 = st.tabs([
        "🔐 1. किसान लॉगिन व खेत सलाह (My Plot & Weather)",
        "📸 2. सिंचाई, खर्च व फसल फोटो (Log Event)",
        "➕ 3. नया किसान / खतौनी व नक्शा पंजीकरण (New Join)"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: MOBILE DIGIT LOGIN + PERSONALIZED PLOT + LIVE WEATHER + MAP
    # --------------------------------------------------------------------------
    with m_tab1:
        st.markdown("#### 🔐 किसान लॉगिन (Farmer Login - अपने खेत का डेटा देखें)")
        col_log1, col_log2 = st.columns([2, 2])
        with col_log1:
            login_query = st.text_input(
                "📱 मोबाइल नंबर (या अंतिम 4 अंक) / खतौनी संख्या दर्ज करें:",
                value="",
                placeholder="उदा: 1122 (Praveen) या 3344 (Srinivas) या खतौनी 142"
            ).strip()
        with col_log2:
            st.info("💡 **डेमो लॉगिन कोड:**\n- **Praveen Kumar:** `1122` (या `9837001122`)\n- **K Srinivas:** `3344` (या `9837003344`)")

        if login_query:
            mask = (
                df['Mobile'].astype(str).str.contains(login_query, case=False, na=False) |
                df['FarmerName'].astype(str).str.contains(login_query, case=False, na=False) |
                (df['KhatauniNo'].astype(str) == login_query) |
                (df['SubPlotID'].astype(str).str.upper() == login_query.upper())
            )
            farmer_df = df[mask].copy()
            if len(farmer_df) > 0:
                matched_names = ", ".join(farmer_df['FarmerName'].unique())
                st.success(f"✅ स्वागत है **{matched_names}**! आपके नाम पर **{len(farmer_df)} सब-प्लॉट ({farmer_df['SubPlotKB'].sum()} कच्चा बीघा)** पंजीकृत हैं।")
            else:
                st.warning("⚠️ इस नंबर/कोड से कोई खेत नहीं मिला। नीचे सभी प्लॉट दिखाए जा रहे हैं या टैब 3 में नया पंजीकरण करें।")
                farmer_df = df.copy()
        else:
            st.caption("ℹ️ ऊपर अपना मोबाइल नंबर (अंतिम 4 अंक) डालें ताकि केवल आपके खेत दिखें। अभी सभी प्लॉट्स उपलब्ध हैं:")
            farmer_df = df.copy()

        sel_sub = st.selectbox(
            "📍 अपना खेत / सब-प्लॉट चुनें (Select Your Sub-Plot):",
            farmer_df['SubPlotID'].unique(),
            format_func=lambda x: f"{x} — {farmer_df[farmer_df['SubPlotID']==x]['Village'].iloc[0]} ({farmer_df[farmer_df['SubPlotID']==x]['SubPlotKB'].iloc[0]} KB | {farmer_df[farmer_df['SubPlotID']==x]['FarmerName'].iloc[0]})"
        )
        r = farmer_df[farmer_df['SubPlotID'] == sel_sub].iloc[0]

        # Fetch Live Weather for this Plot's GPS Coordinates
        lat_val = float(r.get('Latitude', 27.3212))
        lon_val = float(r.get('Longitude', 78.0845))
        wx = fetch_live_weather(lat_val, lon_val)

        # Dynamic Weather & Pest Early Warning Logic
        wx_alerts = []
        if wx['rain_3d'] >= 5.0:
            wx_alerts.append(f"🌧️ **सिंचाई बचत अलर्ट (Rain Alert):** अगले 3 दिनों में **{wx['rain_3d']} mm** बारिश की संभावना है। अभी सिंचाई रोकें और डीजल/बिजली का खर्च बचाएं!")
        else:
            wx_alerts.append("☀️ **मौसम साफ है (No Rain Forecast):** अगले 3 दिनों में बारिश नहीं है। मिट्टी की नमी अनुसार समय पर सिंचाई करें।")

        if wx['rh'] >= 70 and 15 <= wx['temp'] <= 26:
            wx_alerts.append(f"🐛 **माहू (Aphid) चेतावनी:** हवा में नमी **{wx['rh']}%** है। सरसों में माहू कीट की निगरानी करें।")
        if wx['wind'] >= 15.0:
            wx_alerts.append(f"💨 **तेज हवा अलर्ट ({wx['wind']} km/h):** अभी स्प्रे न करें, दवा हवा में उड़ सकती है।")

        st.markdown("#### 🌦️ लाइव मौसम और कृषि चेतावनी (Live Location Weather & Alerts)")
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("🌡️ तापमान (Temp)", f"{wx['temp']} °C", f"ET₀: {wx['et0']} mm/day")
        w2.metric("💧 नमी (Humidity)", f"{wx['rh']} %")
        w3.metric("🌧️ 3-दिन बारिश पूर्वानुमान", f"{wx['rain_3d']} mm")
        w4.metric("💨 हवा की गति (Wind)", f"{wx['wind']} km/h")
        for al in wx_alerts:
            st.info(al)

        col_card, col_map = st.columns([3, 2])
        with col_card:
            st.markdown(f"""
            <div style="background-color:#f1f8e9; padding:20px; border-radius:12px; border:3px solid #2e7d32;">
                <h3 style="color:#1b5e20; margin-top:0;">🌾 किसान सलाह और आर्थिक पासबुक ({r['FarmerName']})</h3>
                <p style="font-size:16px;"><b>गाँव / खसरा:</b> {r['Village']} (Khatauni: {r['KhatauniNo']}, {r['KhasraGata']}) | <b>प्लॉट:</b> {r['SubPlotID']} ({r['Elevation']})</p>
                <p style="font-size:15px;"><b>क्षेत्रफल:</b> {r['SubPlotKB']} कच्चा बीघा ({r['KhatauniHa']} Ha कुल खाता) | <b>मोबाइल:</b> {r['Mobile']}</p>
                <p style="font-size:15px;"><b>वर्तमान फसल:</b> {r['Present_Crop']} ({r['Seed_Variety']}) | <b>मिट्टी pH:</b> {r['pH']} | <b>बोरॉन:</b> {r['B']} ppm</p>
                <hr style="border:1px solid #81c784;">
                <h4 style="color:#b71c1c; margin-bottom:6px;">📅 अगले 40 दिनों का ज़रूरी कार्य:</h4>
                <ol style="font-size:15.5px; line-height:1.6;">
                    <li><b>बेसल खाद सिफारिश ({r['SubPlotKB']} KB हेतु):</b> यूरिया: <b>{r['Rec_Urea_kg']} kg</b> | SSP: <b>{r['Rec_SSP_kg']} kg</b> | पोटाश (MOP): <b>{r['Rec_MOP_kg']} kg</b> | जिप्सम: <b>{r['Rec_Gypsum_kg']} kg</b></li>
                    <li><b>सिंचाई और यूरिया:</b> {'<b>⚠️ रेतीली मिट्टी (22–25 दिन पर):</b> पहली सिंचाई हल्की करें। पानी से पहले यूरिया + ह्यूमिक एसिड डालें।' if 'MP' in str(r['FarmCode']) else '<b>30–35 दिन पर:</b> पहली सिंचाई से ठीक पहले यूरिया की टॉप-ड्रेसिंग करें।'}</li>
                    <li><b>बोरॉन स्प्रे (38–42 दिन):</b> {'इस खेत में बोरॉन की कमी (' + str(r['B']) + ' ppm) है। फूल आने से पहले <b>इफको बोरॉन 20% (1.5 ग्राम/लीटर)</b> का स्प्रे करें।' if r['B']<0.5 else 'फसल वृद्धि के लिए जैव-उत्प्रेरक का स्प्रे करें।'}</li>
                </ol>
                <hr style="border:1px solid #81c784;">
                <p style="font-size:16px; color:#1b5e20;"><b>💰 इस प्लॉट की अनुमानित लागत:</b> ₹{r['Total_CoP_INR']:,.0f} | <b>अनुमानित पैदावार:</b> {r['Pred_Total_Yield_Q']} क्विंटल | <b>शुद्ध लाभ:</b> ₹{r['Net_Profit_Smart_INR']:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

        with col_map:
            st.markdown(f"**🗺️ खेत की जीपीएस लोकेशन ({lat_val:.4f}, {lon_val:.4f})**")
            map_df = farmer_df[['Latitude', 'Longitude', 'SubPlotID']].copy()
            map_df = map_df.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
            st.map(map_df, zoom=12)

    # --------------------------------------------------------------------------
    # TAB 2: LOG IRRIGATION, EXPENSE & CROP PHOTO
    # --------------------------------------------------------------------------
    with m_tab2:
        st.subheader("📸 फसल की फोटो और सिंचाई / खर्च दर्ज करें")
        with st.form("mobile_update_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("किसान का नाम (Farmer Name)")
                f_mob = st.text_input("मोबाइल नंबर (अंतिम 4 अंक या पूरा नंबर)", placeholder="1122")
                f_plot = st.selectbox("प्लॉट चुनें", list(df['SubPlotID'].unique()) + ["ALL (सभी खेत)"])
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
                    "Mobile": f_mob if f_mob else "-",
                    "Village": "Local", "SubPlotID": f_plot.split(" ")[0],
                    "Present_Crop": "Mustard", "Seed_Variety": "Pioneer", "DAS": 30, "Growth_Stage": "Vegetative",
                    "Category": f_cat, "Input_Qty": "1", "Amount_INR": f_amt, "CropCondition": f_cond, "Notes": f_notes
                }])
                pd.concat([logs_df, new_log], ignore_index=True).to_csv(LOGS_CSV, index=False, encoding='utf-8-sig')
                st.success(f"✅ डेटा सेव हो गया! खर्च: ₹{f_amt:,.0f}")
                if "Yellowing" in f_cond:
                    st.warning("🚨 **सलाह:** नाइट्रोजन/सल्फर की कमी हो सकती है। यूरिया + ह्यूमिक एसिड दें और NPK 19:19:19 का स्प्रे करें।")

    # --------------------------------------------------------------------------
    # TAB 3: NEW FARMER REGISTRATION + KHATAUNI EXTRACTOR + GPS VILLAGE FALLBACK
    # --------------------------------------------------------------------------
    with m_tab3:
        st.subheader("➕ नया किसान पंजीकरण (खतौनी अपलोड और जीपीएस लोकेशन के साथ)")

        st.markdown("##### 📄 स्टेप 1 (वैकल्पिक): अपनी खतौनी (UP Bhulekh PDF / Text / Photo) अपलोड करें")
        st.caption("खतौनी अपलोड करने पर हमारा मॉडल अपने आप **हेक्टेयर (Ha)** को **आगरा कच्चा बीघा (1 Ha = 11.86 KB)** में बदल देगा। यदि खतौनी नहीं है, तो सीधे नीचे फॉर्म भरें।")
        uploaded_khatauni = st.file_uploader("📄 खतौनी फ़ाइल चुनें (PDF / TXT / HTML / Image)", type=["pdf", "txt", "html", "png", "jpg", "jpeg"])

        auto_ha = 0.3372
        auto_kb = 4.0
        auto_khatauni_no = 100
        auto_gata = "Gata 101"

        if uploaded_khatauni is not None:
            ext_ha, ext_kno, ext_gata, char_len = extract_khatauni_info(uploaded_khatauni)
            if ext_ha is not None:
                auto_ha = round(ext_ha, 4)
                auto_kb = round(ext_ha / 0.0843, 1)
                st.success(f"✅ खतौनी से क्षेत्रफल मिल गया: **{auto_ha} Hectare** = **{auto_kb} कच्चा बीघा (Agra KB)**")
            else:
                st.info("📄 खतौनी फ़ाइल जुड़ गई है! कृपया नीचे हेक्टेयर या कच्चा बीघा की पुष्टि करें।")
            if ext_kno:
                auto_khatauni_no = ext_kno
            if ext_gata:
                auto_gata = ext_gata

        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            input_ha = st.number_input("📐 खतौनी क्षेत्रफल (Hectare में - यदि पता हो):", min_value=0.01, max_value=50.0, value=float(auto_ha), step=0.05, format="%.4f")
        with calc_col2:
            calculated_kb = round(input_ha / 0.0843, 1)
            st.metric("🔄 आगरा कच्चा बीघा (Auto-Converted KB)", f"{calculated_kb} कच्चा बीघा", "1 Ha = 11.86 KB")

        with st.form("new_farmer_form", clear_on_submit=True):
            nf1, nf2 = st.columns(2)
            with nf1:
                nf_name = st.text_input("किसान का नाम (Farmer Name)*")
                nf_mobile = st.text_input("मोबाइल नंबर (10 अंक - लॉगिन के लिए)*", placeholder="9837XXXXXX")
                nf_village_choice = st.selectbox("गाँव चुनें (Village - स्वतः GPS कोऑर्डिनेट के लिए):", list(VILLAGE_COORDS.keys()))
                nf_custom_village = st.text_input("यदि अन्य गाँव है तो नाम लिखें (Optional):")
                nf_khatauni = st.number_input("खतौनी संख्या (Khatauni No)", min_value=1, value=int(auto_khatauni_no))
                nf_gata = st.text_input("खसरा / गाटा संख्या (Khasra/Gata)", value=auto_gata)
            with nf2:
                nf_kb = st.number_input("खेत का क्षेत्रफल (कच्चा बीघा)", min_value=0.5, value=float(calculated_kb), step=0.5)
                nf_soil = st.selectbox("मिट्टी का प्रकार", ["Loamy (दोमट)", "Sandy Loam (बलुई दोमट)", "Sandy Alkaline (रेतीली क्षारीय)"])
                prev_crop = st.selectbox("पिछले सीजन में कौन सी फसल थी?", ["Bajra (बाजरा - Kharif)", "Fallow (खाली खेत)", "Moong / ढैंचा (दलहन)", "Paddy (धान)"])
                prev_yield = st.number_input("पिछली पैदावार (क्विंटल)", value=6.0)
                prev_irrig = st.number_input("पिछली सिंचाई संख्या", value=2)

                v_info = VILLAGE_COORDS[nf_village_choice]
                use_custom_gps = st.checkbox("📍 क्या आप मैन्युअल GPS (Latitude/Longitude) डालना चाहते हैं? (नहीं चुनने पर गाँव का GPS अपने आप लगेगा)")
                nf_lat = st.number_input("Latitude (अक्षांश)", value=float(v_info["lat"]), format="%.4f")
                nf_lon = st.number_input("Longitude (देशांतर)", value=float(v_info["lon"]), format="%.4f")

            nf_submit = st.form_submit_button("🌾 किसान पंजीकृत करें (Register Farmer & Generate Plot Advisory)")
            if nf_submit and nf_name:
                v_info = VILLAGE_COORDS[nf_village_choice]
                final_lat = nf_lat if use_custom_gps else v_info["lat"]
                final_lon = nf_lon if use_custom_gps else v_info["lon"]
                final_village = nf_custom_village.strip() if nf_custom_village.strip() else nf_village_choice
                f_code = v_info["code"]
                new_id = f"{f_code}-{len(df)+1}"

                proxy = {
                    "pH": 8.1, "EC": 0.65, "OC": 0.40, "N": 74.0, "P": 19, "K": 155,
                    "S": 12.5, "Zn": 0.85, "B": 0.48, "Fe": 5.4, "Mn": 3.8, "Cu": 0.40,
                    "Rec_Urea_kg": round(18.3 * nf_kb, 1),
                    "Rec_SSP_kg": round(21.0 * nf_kb, 1),
                    "Rec_MOP_kg": round(5.5 * nf_kb, 1),
                    "Rec_Gypsum_kg": round(10.5 * nf_kb, 1),
                    "Rec_Borax_kg": round(0.84 * nf_kb, 2)
                }
                new_row = pd.DataFrame([{
                    "FarmCode": f_code, "FarmerName": nf_name, "Village": final_village,
                    "KhatauniNo": int(nf_khatauni), "KhasraGata": nf_gata,
                    "KhatauniHa": round(nf_kb * 0.0843, 4), "TotalKachhaBigha": nf_kb,
                    "SubPlotID": new_id, "Elevation": "MEDIUM", "SubPlotKB": nf_kb, **proxy,
                    "Mobile": nf_mobile if nf_mobile else "9837009999",
                    "Soil_Texture": nf_soil, "Present_Crop": "Mustard (सरसों - Rabi)",
                    "Seed_Variety": "Pioneer 45S46", "Sowing_Date": datetime.now().strftime("%Y-%m-%d"),
                    "Irrigation_Source": "Tube-well", "Prev_Season_Crop": prev_crop,
                    "Prev_Yield_Q": prev_yield, "Prev_Irrigation_Count": prev_irrig,
                    "Prev_Residue_Mgmt": "Standard", "Prev_Disease_History": "None",
                    "Latitude": final_lat, "Longitude": final_lon
                }])
                pd.concat([df, new_row], ignore_index=True).to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')
                st.success(f"🎉 बधाई हो **{nf_name}**! आपका प्लॉट कोड **{new_id}** और GPS लोकेशन ({final_lat}, {final_lon}) सेव हो गया है। अब आप अपने मोबाइल नंबर (`{nf_mobile[-4:] if len(nf_mobile)>=4 else nf_mobile}`) से लॉगिन कर सकते हैं!")
                st.rerun()

# ==============================================================================
# MODE 2: ADMIN & RESEARCH DASHBOARD (PROTECTED BY PIN 2026)
# ==============================================================================
else:
    st.title("🌾 Agri DSS: Admin & Research Dashboard (40-Column Master)")
    pin_input = st.sidebar.text_input("🔒 Enter Admin PIN to Unlock:", type="password", placeholder="Enter PIN (2026)")

    if pin_input != ADMIN_PIN:
        st.warning("🔒 **Admin Access Required:** Please enter the Admin PIN (`2026`) in the left sidebar to view and edit the master 40-column database.")
        st.stop()

    st.sidebar.success("🔓 Admin Mode Unlocked")
    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Expense Audit",
        "🧪 40-Column Master Database",
        "🗺️ Regional Spatial Map",
        "🗄️ Excel Admin Editor"
    ])

    with tab1:
        st.subheader("Ground-Truth Cost Breakdown")
        st.metric("Total Incurred Cost", f"₹{total_incurred:,.0f}", f"₹{grand_total_cop/total_area_kb:,.0f} / KB")
        st.dataframe(logs_df, use_container_width=True)

    with tab2:
        st.subheader("Complete 40-Column Master Database (With GPS Coordinates & Mobile Logins)")
        st.dataframe(df, use_container_width=True)

    with tab3:
        st.subheader("🗺️ All Registered Sub-Plots Across Khandauli / Etmadpur Villages")
        admin_map_df = df[['Latitude', 'Longitude', 'SubPlotID', 'Village', 'FarmerName']].rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
        st.map(admin_map_df, zoom=12)

    with tab4:
        st.subheader("🗄️ Spreadsheet Admin Editor")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Changes"):
            edited_df.to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')
            st.success("✅ Master Database Saved Successfully!")
            st.rerun()
