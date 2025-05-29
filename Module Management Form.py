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

@st.cache_resource(show_spinner=False)
def cached_connect_google_sheet(sheet_name):
    return connect_google_sheet(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

@st.cache_data(ttl=300)
def get_cached_col_values(_worksheet_name, col_index):
    sheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(_worksheet_name)
    return worksheet.col_values(col_index)

def get_last_id(_worksheet_name, prefix):
    try:
        records = get_cached_col_values(_worksheet_name, 1)[1:]
        nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix) and r.split('-')[-1].isdigit()]
        next_num = max(nums) + 1 if nums else 1
        return f"{prefix}-{str(next_num).zfill(3)}"
    except Exception as e:
        st.error(f"⚠️ Failed to generate ID: {e}")
        return f"{prefix}-ERR"

@st.cache_data(ttl=300)
def get_all_records_cached(_worksheet_name):
    sheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(_worksheet_name)
    return worksheet.get_all_records()

# --------------- MAIN SCRIPT ----------------
st.title("🛠 Module Management Form")

# Connect and Setup Tabs
spreadsheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
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
existing_module_ids = get_cached_col_values(TAB_MODULE, 1)[1:]

# ------------------ MODULE TABLE FORM ------------------
st.subheader("🔹 Module Table")
with st.form("module_form"):
    module_id = get_last_id(TAB_MODULE, "MOD")
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
    failure_id = get_last_id(TAB_FAILURES, "FAIL")
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

leak_id = get_last_id(TAB_LEAK, "LEAK")
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
    st.session_state["leak_points"] = []

# ------------------ 7-DAYS DATA PREVIEW ------------------
st.subheader("📅 Records (Last 7 Days)")

def filter_last_7_days(records, date_key):
    today = datetime.today()
    cutoff_date = today - timedelta(days=7)
    filtered_records = []

    for record in records:
        raw_date = record.get(date_key, "")
        date_str = str(raw_date).strip()

        if not date_str:
            continue  # skip if empty

        parsed_date = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

        if not parsed_date:
            # Show warning only for invalid (non-empty) date values
            st.warning(f"⚠️ Skipping record with unrecognized date format: {date_str}\n{record}")
            continue

        if parsed_date.date() >= cutoff_date.date():
            filtered_records.append(record)

    return filtered_records


try:
    module_data = pd.DataFrame(get_all_records_cached(TAB_MODULE))
    failure_data = pd.DataFrame(get_all_records_cached(TAB_FAILURES))
    leak_data = pd.DataFrame(get_all_records_cached(TAB_LEAK))

    # Show Module Table fully (no date filtering needed)
    if not module_data.empty:
        st.subheader("📦 Module Table")
        st.dataframe(module_data)

    # Failures (Last 7 Days)
    if not failure_data.empty:
        st.subheader("🚨 Module Failures Table (Last 7 Days)")
    filtered_failure = filter_last_7_days(failure_data.to_dict(orient="records"), "Date")
    if filtered_failure:
        st.dataframe(pd.DataFrame(filtered_failure))
    else:
        st.info("No failure records in the last 7 days.")

# Leaks (Last 7 Days)
    if not leak_data.empty:
        st.subheader("💧 Leak Test Table (Last 7 Days)")
    filtered_leak = filter_last_7_days(leak_data.to_dict(orient="records"), "Date/Time")
    if filtered_leak:
        st.dataframe(pd.DataFrame(filtered_leak))
    else:
        st.info("No leak test records in the last 7 days.")


except Exception as e:
    st.error(f"❌ Error loading recent data: {e}")
