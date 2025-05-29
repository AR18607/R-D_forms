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
@st.cache_resource(show_spinner=False)
def cached_connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

spreadsheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)


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

# ------------------ MODULE TABLE FORM ------------------
st.subheader("🔹 Module Table")
with st.form("module_form"):
    module_id = get_last_id(module_sheet, "MOD")
    st.markdown(f"**Auto-generated Module ID:** `{module_id}`")
    module_type = st.selectbox("Module Type", ["Wound", "Mini"])
    module_notes = st.text_area("Module Notes")
    submit_module = st.form_submit_button("🚀 Submit Module")

if submit_module:
    module_sheet.append_row([module_id, module_type, module_notes])
    st.success(f"✅ Module {module_id} saved successfully!")

# ------------------ MODULE FAILURE FORM ------------------
st.subheader("🔹 Module Failure Table")
with st.form("failure_form"):
    failure_id = get_last_id(failure_sheet, "FAIL")
    failure_module_fk = st.selectbox("Module ID (Failure)", existing_module_ids)
    failure_description = st.text_area("Failure Description")
    autopsy = st.selectbox("Autopsy Done?", ["Yes", "No"])
    autopsy_notes = st.text_area("Autopsy Notes")
    microscopy = st.selectbox("Microscopy Type", ["Classical", "SEM", "None"])
    microscopy_notes = st.text_area("Microscopy Notes")
    failure_mode = st.text_input("Failure Mode")
    failure_operator = st.text_input("Failure Operator Initials")
    failure_date = st.date_input("Failure Date")
    failure_label = st.text_input("Failure Label")
    submit_failure = st.form_submit_button("🚨 Submit Failure Entry")

if submit_failure:
    failure_sheet.append_row([
        failure_id, failure_module_fk, failure_description, autopsy, autopsy_notes,
        microscopy, microscopy_notes, failure_mode, failure_operator, str(failure_date), failure_label
    ])
    st.success(f"✅ Failure Entry {failure_id} saved successfully!")

# ------------------ LEAK TEST FORM (SUPPORT MULTIPLE ENTRIES) ------------------
st.subheader("🔹 Leak Test Table (Multi-Entry)")

if "leak_points" not in st.session_state:
    st.session_state["leak_points"] = []

leak_id = get_last_id(leak_sheet, "LEAK")
leak_module_fk = st.selectbox("Module ID (Leak)", existing_module_ids)
leak_end = st.selectbox("End", ["Plug", "Nozzle"])
leak_test_type = st.selectbox("Leak Test Type", ["Water", "N2"])
leak_operator = st.text_input("Operator Initials")
leak_notes = st.text_area("Notes")
leak_date = st.date_input("Leak Date/Time", value=datetime.today())

st.markdown("### ➕ Add Leak Points")

with st.form("add_leak_point_form"):
    leak_location = st.selectbox("Leak Location", ["Fiber", "Potting"], key="location_entry")
    repaired = st.selectbox("Repaired?", ["Yes", "No"], key="repaired_entry")
    add_point = st.form_submit_button("➕ Add Leak Point")

if add_point:
    st.session_state["leak_points"].append({
        "Leak Location": leak_location,
        "Repaired": repaired
    })
    st.success("Leak point added.")

if st.session_state["leak_points"]:
    st.markdown("### 📋 Pending Leak Points")
    st.dataframe(pd.DataFrame(st.session_state["leak_points"]))

if st.button("💧 Submit All Leak Points"):
    for point in st.session_state["leak_points"]:
        leak_sheet.append_row([
            leak_id, leak_module_fk, leak_end, leak_test_type, point["Leak Location"],
            1, point["Repaired"], leak_operator, leak_notes, leak_date.strftime("%Y-%m-%d")
        ])
    st.success(f"✅ {len(st.session_state['leak_points'])} Leak Points saved under Leak ID {leak_id}")
    st.session_state["leak_points"] = []  # clear after submit


# ------------------ 7-DAYS DATA PREVIEW ------------------
st.subheader("📅 Records (Last 7 Days)")

def filter_last_7_days(records, date_key):
    """Filters records based on Date column, keeping only last 7 days."""
    today = datetime.today()
    filtered_records = []
    for record in records:
        date_str = record.get(date_key, "").strip()
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            if parsed_date.date() >= (today - timedelta(days=7)).date():
                filtered_records.append(record)
        except ValueError:
            pass  # Skip records with invalid dates
    return filtered_records

# Load & Filter Data
try:
    module_data = pd.DataFrame(module_sheet.get_all_records())
    failure_data = pd.DataFrame(failure_sheet.get_all_records())
    leak_data = pd.DataFrame(leak_sheet.get_all_records())

    if not module_data.empty:
        st.subheader("📦 Module Table")
        st.dataframe(module_data)

    if not failure_data.empty:
        st.subheader("🚨 Module Failures Table (Last 7 Days)")
        filtered_failure = filter_last_7_days(failure_data.to_dict(orient="records"), "Date")
        st.write(pd.DataFrame(filtered_failure) if filtered_failure else "No failure records in the last 7 days.")

    if not leak_data.empty:
        st.subheader("💧 Leak Test Table (Last 7 Days)")
        filtered_leak = filter_last_7_days(leak_data.to_dict(orient="records"), "Date/Time")
        st.write(pd.DataFrame(filtered_leak) if filtered_leak else "No leak test records in the last 7 days.")

except Exception as e:
    st.error(f"❌ Error loading recent data: {e}")

# ------------------ OPTIONAL EDIT VIEW & COLUMNS CLARITY ------------------
st.markdown("---")
st.markdown("### ℹ️ Notes")
st.markdown("- Use **clear labels** for all fields; consult team if column names are unclear.")
st.markdown("- Editing/viewing of existing entries will be added in a future release.")
