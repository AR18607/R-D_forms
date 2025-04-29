import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------- CONFIGURATION ----------------

GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MODULE = "Module Tbl"
TAB_PRESSURE_TEST = "Pressure Test Tbl"

# ---------------- CONNECTION FUNCTIONS ----------------

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
    records = worksheet.col_values(1)[1:]  # Skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

# ---------------- MAIN APP ----------------

st.title("🧪 Testing Form")

# Connect to Google Sheets
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Tabs
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
pressure_test_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow", "Pressure Test Date & Time",
    "Operator Initials", "Notes", "Passed"
])

# Fetch Existing Module IDs
existing_module_ids = module_sheet.col_values(1)[1:]  # Skip header

# ---------------- FORM ----------------

with st.form("pressure_test_form"):
    st.subheader("🔹 Pressure Test Entry")

    pressure_test_id = get_last_id(pressure_test_sheet, "PT")
    st.markdown(f"**Auto-generated Pressure Test ID:** `{pressure_test_id}`")

    module_id = st.selectbox("Select Module ID", existing_module_ids) if existing_module_ids else st.text_input("Module ID (Manual Entry)")

    feed_pressure = st.number_input("Feed Pressure (psi)", format="%.2f")
    permeate_flow = st.number_input("Permeate Flow (L/min)", format="%.2f")

    # Corrected: separate date and time inputs
    test_date = st.date_input("Pressure Test Date", datetime.now())
    test_time = st.time_input("Pressure Test Time", datetime.now().time())
    test_datetime = datetime.combine(test_date, test_time)

    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Test Notes")
    passed = st.selectbox("Passed?", ["Yes", "No"])

    submit_button = st.form_submit_button("🚀 Submit Pressure Test Record")

# ---------------- SAVE DATA ----------------

if submit_button:
    try:
        pressure_test_sheet.append_row([
            pressure_test_id,
            module_id,
            feed_pressure,
            permeate_flow,
            str(test_datetime),
            operator_initials,
            notes,
            passed
        ])
        st.success("✅ Pressure Test Record Successfully Saved!")
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")

# ---------------- OPTIONAL: Weekly View ----------------

st.subheader("📅 Recent Pressure Test Records")

try:
    records = pressure_test_sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df)
    else:
        st.info("No records found.")
except Exception as e:
    st.error(f"❌ Error fetching records: {e}")
