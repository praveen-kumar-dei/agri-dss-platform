import os
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Agri DSS | किसान मित्र पोर्टल",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

MASTER_CSV = "Agri_DSS_Live.csv"
LOGS_CSV = "farmer_field_logs_v2.csv"

def init_databases():
    if not os.path.exists(MASTER_CSV):
        pd.DataFrame([{ 'FarmCode': 'NC', 'FarmerName': 'Praveen Kumar', 'Village': 'Nagla Chatura (नगला चतुर)', 'KhatauniNo': 142, 'KhasraGata': 'Gata 218', 'KhatauniHa': 1.0, 'TotalKachhaBigha': 12, 'SubPlotID': 'NCH', 'Elevation': 'HIGH', 'SubPlotKB': 3.0, 'pH': 8.1, 'EC': 0.9, 'OC': 0.4, 'N': 75.0, 'P': 18, 'K': 210, 'S': 12.0, 'Zn': 0.7, 'B': 0.7, 'Fe': 4.9, 'Mn': 3.8, 'Cu': 0.4, 'Rec_Urea_kg': 55.0, 'Rec_SSP_kg': 63.2, 'Rec_MOP_kg': 10.5, 'Rec_Gypsum_kg': 31.6, 'Rec_Borax_kg': 0.0, 'Mobile': '98XXXXXXXX', 'Soil_Texture': 'Loamy', 'Present_Crop': 'Mustard', 'Seed_Variety': 'Pioneer 45S46', 'Sowing_Date': '2026-10-15', 'Irrigation_Source': 'Tube-well', 'Prev_Season_Crop': 'Bajra', 'Prev_Yield_Q': 5.4, 'Prev_Irrigation_Count': 2, 'Prev_Residue_Mgmt': 'Removed', 'Prev_Disease_History': 'None'}]).to_csv(MASTER_CSV, index=False, encoding='utf-8-sig')
    if not os.path.exists(LOGS_CSV):
        pd.DataFrame([{"Timestamp": "2026-10-10 09:00", "FarmerName": "Baseline", "Mobile": "-", "Village": "All", "SubPlotID": "ALL", "Present_Crop": "Mustard", "Seed_Variety": "Standard", "DAS": 5, "Growth_Stage": "Germination", "Category": "Land Preparation", "Input_Qty": "Cultivator", "Amount_INR": 20000.0, "CropCondition": "Healthy", "Notes": "Land prep"}]).to_csv(LOGS_CSV, index=False, encoding='utf-8-sig')

init_databases()
df = pd.read_csv(MASTER_CSV)
logs_df = pd.read_csv(LOGS_CSV)

st.sidebar.title("🌾 Agri DSS किसान पोर्टल")
app_mode = st.sidebar.radio("📲 Select Mode:", ["📱 किसान मोबाइल ऐप (Farmer Easy Mode)", "🖥️ Full Admin & Research Dashboard"])

total_area_kb = df['SubPlotKB'].sum() if 'SubPlotKB' in df.columns else 34.0
total_incurred = logs_df['Amount_INR'].sum()

if app_mode == "📱 किसान मोबाइल ऐप (Farmer Easy Mode)":
    st.title("🌾 किसान मित्र (Farmer Support App)")
    sel_sub = st.selectbox("📍 अपना खेत / सब-प्लॉट चुनें:", df['SubPlotID'].unique())
    r = df[df['SubPlotID'] == sel_sub].iloc[0]
    st.success(f"Selected Plot: {r['SubPlotID']} | Village: {r['Village']} | Area: {r['SubPlotKB']} KB | pH: {r['pH']} | Boron: {r['B']} ppm")
    st.dataframe(df)
else:
    st.title("🌾 Agri DSS: Admin & Research Dashboard")
    st.write(f"Total Sub-Plots Loaded: {len(df)}")
    st.dataframe(df)
