import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ----------------- CONFIG -----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_PURE_GAS_TEST = "Pure Gas Test Tbl"

# ----------------- CONNECTION FUNCTIONS -----------------

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

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]  # skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def fetch_module_ids(spreadsheet):
    try:
        module_sheet = spreadsheet.worksheet("Module Tbl")
        ids = module_sheet.col_values(1)[1:]  # Skip header
        return ids
    except gspread.exceptions.WorksheetNotFound:
        return []

# ----------------- STREAMLIT APP -----------------

st.title("🧪 Pure Gas Test Form")

# Connect to sheet
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Ensure tab exists
puregas_sheet = get_or_create_tab(spreadsheet, TAB_PURE_GAS_TEST, [
    "Pure Gas Test ID", "Test Date", "Module ID", "Gas", "Pressure",
    "Flow", "Operator Initials", "Notes", "Permeance", "Selectivity", "Passed"
])

# Fetch Module IDs
module_ids = fetch_module_ids(spreadsheet)

# Form
with st.form("pure_gas_test_form"):
    st.subheader("🔹 Pure Gas Test Entry")
    
    pure_gas_test_id = get_last_id(puregas_sheet, "PGT")
    st.markdown(f"**Auto-generated Pure Gas Test ID:** `{pure_gas_test_id}`")

    test_date = st.date_input("Test Date")
    if module_ids:
        selected_module = st.selectbox("Select Module ID", module_ids)
    else:
        selected_module = st.text_input("Enter Module ID (No modules found!)")

    gas_type = st.selectbox("Gas Type", ["CO2", "N2", "O2"])
    pressure = st.number_input("Pressure", format="%.2f")
    flow = st.number_input("Flow", format="%.2f")
    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    permeance = st.number_input("C-Permeance (Requires module area)", format="%.2f")
    selectivity = st.number_input("C-Selectivity", format="%.2f")
    passed = st.selectbox("Passed?", ["Yes", "No"])

    submit_button = st.form_submit_button("🚀 Submit")

# Save
if submit_button:
    try:
        passed_bool = True if passed == "Yes" else False
        puregas_sheet.append_row([
            pure_gas_test_id,
            str(test_date),
            selected_module,
            gas_type,
            pressure,
            flow,
            operator_initials,
            notes,
            permeance,
            selectivity,
            passed_bool
        ])
        st.success("✅ Pure Gas Test entry saved successfully!")
    except Exception as e:
        st.error(f"❌ Failed to save entry: {e}")
