import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

# --------------- CONFIG ----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

# Tab Names
TAB_MODULE = "Module Tbl"
TAB_FAILURES = "Module Failures Tbl"
TAB_LEAK = "Leak Test Tbl"

# --------------- GOOGLE SHEET FUNCTIONS ----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
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

# --------------- MAIN SCRIPT ----------------
st.title("🛠 Module Management Form")

# Connect
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Tabs
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
failure_sheet = get_or_create_tab(spreadsheet, TAB_FAILURES, [
    "Module Failure ID", "Module ID (FK)", "Description of Failure", "Autopsy", 
    "Autopsy Notes", "Microscopy", "Microscopy Notes", "Failure Mode", "Operator Initials", 
    "Date", "Label"
])
leak_sheet = get_or_create_tab(spreadsheet, TAB_LEAK, [
    "Leak Test ID", "Module ID (FK)", "End", "Leak Test Type", "Leak Location", 
    "Number of Leaks", "Repaired", "Operator Initials", "Notes", "Date/Time"
])

# Fetch Existing Module IDs
existing_module_ids = module_sheet.col_values(1)[1:]

# Form
with st.form("module_management_form"):

    st.subheader("🔹 Module Table")
    module_id = get_last_id(module_sheet, "MOD")
    st.markdown(f"**Auto-generated Module ID:** `{module_id}`")
    module_type = st.selectbox("Module Type", ["Wound", "Mini"])
    module_notes = st.text_area("Module Notes")

    st.subheader("🔹 Module Failure Table")
    failure_id = get_last_id(failure_sheet, "FAIL")
    if existing_module_ids:
        failure_module_fk = st.selectbox("Module ID (Failure)", existing_module_ids)
    else:
        failure_module_fk = st.text_input("Module ID (Failure FK)")
    failure_description = st.text_area("Failure Description")
    autopsy = st.selectbox("Autopsy Done?", ["Yes", "No"])
    autopsy_notes = st.text_area("Autopsy Notes")
    microscopy = st.selectbox("Microscopy Type", ["Classical", "SEM", "None"])
    microscopy_notes = st.text_area("Microscopy Notes")
    failure_mode = st.text_input("Failure Mode")
    failure_operator = st.text_input("Failure Operator Initials")
    failure_date = st.date_input("Failure Date")
    failure_label = st.text_input("Failure Label")

    st.subheader("🔹 Leak Test Table")
    leak_id = get_last_id(leak_sheet, "LEAK")
    if existing_module_ids:
        leak_module_fk = st.selectbox("Module ID (Leak)", existing_module_ids)
    else:
        leak_module_fk = st.text_input("Module ID (Leak FK)")
    leak_end = st.selectbox("End", ["Plug", "Nozzle"])
    leak_test_type = st.selectbox("Leak Test Type", ["Water", "N2"])
    leak_location = st.selectbox("Leak Location", ["Fiber", "Potting"])
    leak_num = st.number_input("Number of Leaks", min_value=0)
    repaired = st.selectbox("Repaired?", ["Yes", "No"])
    leak_operator = st.text_input("Leak Operator Initials")
    leak_notes = st.text_area("Leak Notes")
    leak_date = st.date_input("Leak Date/Time")

    submit_button = st.form_submit_button("🚀 Submit All Entries")

# Save data to Google Sheets
if submit_button:
    try:
        module_sheet.append_row([module_id, module_type, module_notes])
        failure_sheet.append_row([
            failure_id, failure_module_fk, failure_description, autopsy, autopsy_notes,
            microscopy, microscopy_notes, failure_mode, failure_operator, str(failure_date), failure_label
        ])
        leak_sheet.append_row([
            leak_id, leak_module_fk, leak_end, leak_test_type, leak_location,
            leak_num, repaired, leak_operator, leak_notes, str(leak_date)
        ])
        st.success("✅ Data saved successfully across all three tables!")

    except Exception as e:
        st.error(f"❌ Failed to save: {e}")

# Show last 7 days data
st.subheader("📅 Records (Last 7 Days)")

try:
    today = datetime.now()
    last_week = today - timedelta(days=7)

    module_data = pd.DataFrame(module_sheet.get_all_records())
    failure_data = pd.DataFrame(failure_sheet.get_all_records())
    leak_data = pd.DataFrame(leak_sheet.get_all_records())

    if not module_data.empty:
        st.subheader("📦 Module Table")
        st.dataframe(module_data)

    if not failure_data.empty:
        st.subheader("🚨 Module Failures Table")
        st.dataframe(failure_data)

    if not leak_data.empty:
        st.subheader("💧 Leak Test Table")
        st.dataframe(leak_data)

except Exception as e:
    st.error(f"Error loading recent data: {e}")
