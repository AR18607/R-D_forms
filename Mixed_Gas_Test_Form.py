import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------- CONFIG ----------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MIXED_GAS = "Mixed Gas Test Tbl"
TAB_MODULE = "Module Tbl"

# ---------- SHEET SETUP ----------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, prefix):
    records = worksheet.col_values(1)[1:]
    if not records:
        return f"{prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix)]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

# ---------- START ----------
st.title("🧪 Mixed Gas Test Form")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
mixed_gas_sheet = get_or_create_tab(spreadsheet, TAB_MIXED_GAS, [
    "Mixed Gas Test ID", "Mixed Gas Test Date", "Module ID", "Temperature", "Feed Pressure",
    "Retentate Pressure", "Retentate Flow", "Retentate CO2 Comp", "Permeate Pressure", 
    "Permeate Flow", "Permeate CO2 Composition", "Permeate O2 Composition", 
    "Ambient Temperature", "CO2 Analyzer ID", "Test Rig", "Operator Initials", "Notes", "Passed",
    "Module Area", "C-CO2 Perm", "C-N2 Perm", "C-Selectivity", "C-CO2 Flux", "C-stage cut"
])
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
existing_module_ids = module_sheet.col_values(1)[1:]

# ---------- FORM ----------
with st.form("mixed_gas_form"):
    st.subheader("📋 Mixed Gas Test Entry")
    mixed_gas_id = get_last_id(mixed_gas_sheet, "MIXG")
    st.markdown(f"**Auto-generated Test ID:** `{mixed_gas_id}`")

    test_date = st.date_input("Test Date", value=datetime.now())
    module_id = st.selectbox("Module ID (from Module Tbl)", existing_module_ids) if existing_module_ids else st.text_input("Module ID")

    temperature = st.number_input("Temperature (°C)", format="%.2f")
    feed_pressure = st.number_input("Feed Pressure (psi)", format="%.2f")
    retentate_pressure = st.number_input("Retentate Pressure (psi)", format="%.2f")
    retentate_flow = st.number_input("Retentate Flow (L/min)", format="%.2f")
    retentate_co2 = st.number_input("Retentate CO2 Composition (%)", format="%.2f")

    permeate_pressure = st.number_input("Permeate Pressure (psi)", format="%.2f")
    permeate_flow = st.number_input("Permeate Flow (L/min)", format="%.2f")
    permeate_co2 = st.number_input("Permeate CO2 Composition (%)", format="%.2f")
    permeate_o2 = st.number_input("Permeate O2 Composition (%)", format="%.2f")
    ambient_temp = st.number_input("Ambient Temperature (°C)", format="%.2f")

    module_area = st.number_input("Module Area (cm²)", min_value=0.001, format="%.3f")

    analyzer_id = st.text_input("CO2 Analyzer ID")
    test_rig = st.multiselect("Test Rig (Select all that apply)", ["TR-1", "TR-2", "TR-3", "Other"])
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    passed = st.radio("Passed?", ["Yes", "No"]) == "Yes"

    # Manual Permeances (until formulas are finalized)
    c_co2_perm = st.number_input("C - CO2 Permeance", format="%.4f")
    c_n2_perm = st.number_input("C - N2 Permeance", format="%.4f")

    # Auto-calculated values
    c_selectivity = round(c_co2_perm / c_n2_perm, 6) if c_n2_perm else 0
    c_flux = round(permeate_flow / module_area, 6) if module_area else 0
    c_stage_cut = round(permeate_flow / feed_pressure, 6) if feed_pressure else 0

    submitted = st.form_submit_button("🚀 Submit Mixed Gas Test")

# ---------- SUBMIT ----------
if submitted:
    try:
        mixed_gas_sheet.append_row([
            mixed_gas_id, str(test_date), module_id, temperature, feed_pressure,
            retentate_pressure, retentate_flow, retentate_co2, permeate_pressure,
            permeate_flow, permeate_co2, permeate_o2, ambient_temp, analyzer_id,
            ", ".join(test_rig), initials, notes, passed,
            module_area, round(c_co2_perm, 6), round(c_n2_perm, 6),
            c_selectivity, c_flux, c_stage_cut
        ])
        st.success("✅ Mixed Gas Test record saved successfully!")
    except Exception as e:
        st.error(f"❌ Failed to save data: {e}")
