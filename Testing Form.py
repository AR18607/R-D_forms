import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------- CONFIG ----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS_FILE = "rnd-form-sheets-b47d625d6fd9.json"

TAB_PRESSURE_TEST = "Pressure Test Tbl"
TAB_MODULE = "Module Tbl"

# --------------- CONNECTION FUNCTIONS ---------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    import json
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
    next_num = max(nums) + 1
    return f"{prefix}-{str(next_num).zfill(3)}"

# ---------------- STREAMLIT FORM ----------------

st.title("🧪 Pressure Test Form")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
pressure_test_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow",
    "Pressure Test DateTime", "Operator Initials", "Notes", "Passed"
])

# Fetch existing Module IDs
existing_module_ids = module_sheet.col_values(1)[1:]

with st.form("pressure_test_form"):
    st.subheader("🔹 Pressure Test Entry")
    
    pressure_test_id = get_last_id(pressure_test_sheet, "PT")
    st.markdown(f"**Auto-generated Pressure Test ID:** `{pressure_test_id}`")

    if existing_module_ids:
        module_id = st.selectbox("Select Module ID", existing_module_ids)
    else:
        module_id = st.text_input("Module ID (No Module Records Found)", "")
    
    feed_pressure = st.number_input("Feed Pressure (psi)", format="%.2f")
    permeate_flow = st.number_input("Permeate Flow (L/min)", format="%.2f")
    test_datetime = st.datetime_input("Pressure Test Date & Time", datetime.now())
    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Test Notes")
    passed = st.selectbox("Passed?", ["Yes", "No"])

    submit_button = st.form_submit_button("🚀 Submit Pressure Test Record")

if submit_button:
    try:
        passed_bool = True if passed == "Yes" else False
        pressure_test_sheet.append_row([
            pressure_test_id,
            module_id,
            feed_pressure,
            permeate_flow,
            str(test_datetime),
            operator_initials,
            notes,
            passed_bool
        ])
        st.success("✅ Pressure Test record successfully saved!")
    except Exception as e:
        st.error(f"❌ Error saving record: {e}")

