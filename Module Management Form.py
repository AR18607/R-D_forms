import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

# CONFIGURATION
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

# Tab Names
TAB_MODULE = "Module Tbl"
TAB_LEAK = "Leak Test Tbl"
TAB_FAILURES = "Module Failures Tbl"

# Google Sheet functions
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
def get_cached_col_values(sheet_name, col_index):
    sheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(sheet_name)
    return worksheet.col_values(col_index)

@st.cache_data(ttl=300)
def get_all_records_cached(sheet_name):
    sheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(sheet_name)
    return worksheet.get_all_records()

def get_last_id(sheet_name, prefix):
    records = get_cached_col_values(sheet_name, 1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix) and r.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

# Streamlit app
st.title("🛠 Module Management Form")

spreadsheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
leak_sheet = get_or_create_tab(spreadsheet, TAB_LEAK, [
    "Leak Test ID", "Module ID", "Module Type", "End", "Leak Test Type", "Leak Location",
    "Repaired", "Operator Initials", "Notes", "Date/Time"
])
failure_sheet = get_or_create_tab(spreadsheet, TAB_FAILURES, [
    "Module Failure ID", "Module ID", "Description of Failure", "Autopsy", "Autopsy Notes",
    "Microscopy", "Microscopy Notes", "Failure Mode", "Operator Initials", "Date", "Label"
])

existing_modules_df = pd.DataFrame(get_all_records_cached(TAB_MODULE))
module_options = existing_modules_df[['Module ID', 'Module Type']].apply(lambda x: f"{x[0]} ({x[1]})", axis=1).tolist()

# MODULE ENTRY FORM
st.subheader("🔹 Module Entry")
with st.form("module_entry_form", clear_on_submit=True):
    module_id = get_last_id(TAB_MODULE, "MOD")
    st.markdown(f"**Auto-generated Module ID:** `{module_id}`")
    module_type = st.selectbox("Module Type", ["Wound", "Mini"])
    module_notes = st.text_area("Notes")
    if st.form_submit_button("🚀 Submit Module"):
        module_sheet.append_row([module_id, module_type, module_notes])
        st.success(f"✅ Module {module_id} saved successfully!")

# MODULE FAILURE FORM
st.subheader("🔹 Module Failure Entry")
with st.form("failure_entry_form", clear_on_submit=True):
    failure_id = get_last_id(TAB_FAILURES, "FAIL")
    failure_module_fk = st.selectbox("Module ID", module_options)
    description = st.text_area("Description of Failure")
    autopsy = st.selectbox("Autopsy Done?", ["Yes", "No"])
    autopsy_notes = st.text_area("Autopsy Notes")
    microscopy = st.selectbox("Microscopy Type", ["Classical", "SEM", "None"])
    microscopy_notes = st.text_area("Microscopy Notes")
    failure_mode = st.text_input("Failure Mode")
    operator_initials = st.text_input("Operator Initials")
    failure_date = st.date_input("Failure Date")
    label = st.text_input("Label")
    if st.form_submit_button("🚨 Submit Failure Entry"):
        mod_id, _ = failure_module_fk.split(' (')
        failure_sheet.append_row([
            failure_id, mod_id, description, autopsy, autopsy_notes,
            microscopy, microscopy_notes, failure_mode, operator_initials,
            str(failure_date), label
        ])
        st.success(f"✅ Failure Entry {failure_id} saved successfully!")

# LEAK TEST FORM
st.subheader("🔹 Leak Test Entry")
leak_id = get_last_id(TAB_LEAK, "LEAK")
st.markdown(f"**Auto-generated Leak Test ID:** `{leak_id}`")
if "leak_points" not in st.session_state:
    st.session_state["leak_points"] = []

with st.form("leak_entry_form"):
    module_selection = st.selectbox("Module ID", module_options)
    leak_end = st.selectbox("End", ["Plug", "Nozzle"])
    leak_test_type = st.selectbox("Leak Test Type", ["Water", "N2"])
    operator_initials = st.text_input("Operator Initials")
    leak_location = st.selectbox("Leak Location", ["Fiber", "Potting"])
    repaired = st.selectbox("Repaired", ["Yes", "No"])
    leak_notes = st.text_area("Notes")
    add_point = st.form_submit_button("➕ Add Leak Point")
    if add_point:
        st.session_state.leak_points.append({
            "Leak Location": leak_location, "Repaired": repaired, "End": leak_end, "Notes": leak_notes
        })
        st.success("Leak point added.")

if st.session_state.leak_points:
    st.markdown("### 📋 Pending Leak Points")
    st.dataframe(pd.DataFrame(st.session_state.leak_points))
    if st.button("💧 Submit All Leak Points"):
        mod_id, mod_type = module_selection.split(' (')
        mod_type = mod_type.rstrip(')')
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for point in st.session_state.leak_points:
            leak_sheet.append_row([leak_id, mod_id, mod_type, point["End"], leak_test_type,
                                   point["Leak Location"], point["Repaired"], operator_initials,
                                   point["Notes"], date_now])
        st.success(f"✅ Leak points saved under Leak ID {leak_id}")
        st.session_state.leak_points = []

# 7-DAYS DATA REVIEW
st.subheader("📅 Records (Last 7 Days)")
for tab_name, date_col in [(TAB_MODULE, None), (TAB_LEAK, "Date/Time"), (TAB_FAILURES, "Date")]:
    try:
        df = pd.DataFrame(get_all_records_cached(tab_name))
        if not df.empty:
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df[df[date_col] >= datetime.now() - timedelta(days=7)]
            if not df.empty:
                st.markdown(f"### 📋 Recent {tab_name}")
                st.dataframe(df)
            else:
                st.info(f"No recent data in {tab_name}.")
        else:
            st.info(f"No data found in {tab_name}.")
    except Exception as e:
        st.error(f"Error loading {tab_name}: {e}")
