import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

TAB_MODULE = "Module Tbl"
TAB_LEAK = "Leak Test Tbl"
TAB_FAILURES = "Module Failures Tbl"

# Google Sheet connection
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

def get_all_records(tab_name):
    sheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(tab_name)
    return worksheet.get_all_records()

def get_last_id(tab_name, prefix):
    records = get_all_records(tab_name)
    if not records:
        return f"{prefix}-001"
    ids = []
    for r in records:
        for v in r.values():
            if isinstance(v, str) and v.startswith(prefix) and v.split('-')[-1].isdigit():
                ids.append(int(v.split('-')[-1]))
    next_num = max(ids) + 1 if ids else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

# --- MAIN APP ---
st.title("🛠 Module Management Form")

spreadsheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Label", "Notes"])
leak_sheet = get_or_create_tab(spreadsheet, TAB_LEAK, [
    "Leak Test ID", "Module ID", "Module Type", "End", "Leak Test Type", "Leak Location",
    "Repaired", "Operator Initials", "Notes", "Date/Time"
])
failure_sheet = get_or_create_tab(spreadsheet, TAB_FAILURES, [
    "Module Failure ID", "Module ID", "Description of Failure", "Autopsy", "Autopsy Notes",
    "Microscopy", "Microscopy Notes", "Failure Mode", "Operator Initials", "Date", "Label"
])

# Fetch data for dropdowns
modules_df = pd.DataFrame(get_all_records(TAB_MODULE))
failures_df = pd.DataFrame(get_all_records(TAB_FAILURES))

# Helper for combined label in dropdowns
def module_dropdown_label(row):
    # Will look like: MOD-001 / Mini / Label-01
    mid = row.get('Module ID', '')
    mtype = row.get('Module Type', '')
    label = row.get('Label', '')
    return f"{mid} / {mtype} / {label}" if label else f"{mid} / {mtype}"

module_options = modules_df.apply(module_dropdown_label, axis=1).tolist()

# --- MODULE ENTRY FORM ---
st.subheader("🔹 Module Entry")
with st.form("module_entry_form", clear_on_submit=True):
    module_id = get_last_id(TAB_MODULE, "MOD")
    st.markdown(f"**Auto-generated Module ID:** `{module_id}`")
    module_type = st.selectbox("Module Type", ["Wound", "Mini"])
    label = st.text_input("Label (unique for this module, optional)")
    module_notes = st.text_area("Notes")
    if st.form_submit_button("🚀 Submit Module"):
        # Insert Label for future reference in Failure table!
        module_sheet.append_row([module_id, module_type, label, module_notes])
        st.success(f"✅ Module {module_id} saved successfully!")

# --- MODULE FAILURE FORM ---
st.subheader("🔹 Module Failure Entry")
# Unique Module IDs (no repeats in the failures table for dropdown)
used_module_ids = set(failures_df["Module ID"].tolist()) if not failures_df.empty else set()
available_module_rows = modules_df[~modules_df["Module ID"].isin(used_module_ids)]
available_module_options = available_module_rows.apply(module_dropdown_label, axis=1).tolist()
if not available_module_options:
    st.info("All modules already have failures recorded.")

# PK: Module Failure ID
with st.form("failure_entry_form", clear_on_submit=True):
    failure_id = get_last_id(TAB_FAILURES, "FAIL")
    st.markdown(f"**Primary Key (PK):** `{failure_id}`")

    # Option to select by Label to view/edit old details
    all_labels = failures_df["Label"].dropna().unique().tolist() if not failures_df.empty else []
    prev_label = st.selectbox("View by previous Label (for detail lookup):", [""] + all_labels)
    prev_label_details = None
    if prev_label:
        prev_label_details = failures_df[failures_df["Label"] == prev_label].to_dict(orient="records")
        if prev_label_details:
            st.info(f"Details for Label '{prev_label}':\n{prev_label_details[0]}")
    
    failure_module_fk = st.selectbox("Module ID", available_module_options)
    mod_id = failure_module_fk.split(' / ')[0]
    description = st.text_area("Description of Failure")
    autopsy = st.selectbox("Autopsy Done?", ["Yes", "No"])
    autopsy_notes = st.text_area("Autopsy Notes")
    microscopy = st.selectbox("Microscopy Type", ["Classical", "SEM", "None"])
    microscopy_notes = st.text_area("Microscopy Notes")
    failure_mode = st.text_input("Failure Mode")
    operator_initials = st.text_input("Operator Initials")
    failure_date = st.date_input("Failure Date")
    failure_label = st.text_input("Label (connects to previous data)")
    if st.form_submit_button("🚨 Submit Failure Entry"):
        failure_sheet.append_row([
            failure_id, mod_id, description, autopsy, autopsy_notes,
            microscopy, microscopy_notes, failure_mode, operator_initials,
            str(failure_date), failure_label
        ])
        st.success(f"✅ Failure Entry {failure_id} saved successfully!")

# --- LEAK TEST FORM ---
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
        mod_id = module_selection.split(' / ')[0]
        mod_type = modules_df[modules_df['Module ID'] == mod_id]['Module Type'].values[0]
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for point in st.session_state.leak_points:
            leak_sheet.append_row([leak_id, mod_id, mod_type, point["End"], leak_test_type,
                                   point["Leak Location"], point["Repaired"], operator_initials,
                                   point["Notes"], date_now])
        st.success(f"✅ Leak points saved under Leak ID {leak_id}")
        st.session_state.leak_points = []

# --- DATA REVIEW (30 DAYS) ---
st.subheader("📅 Records (Last 30 Days)")
for tab_name, date_col in [(TAB_MODULE, None), (TAB_LEAK, "Date/Time"), (TAB_FAILURES, "Date")]:
    try:
        df = pd.DataFrame(get_all_records(tab_name))
        df.columns = [col.strip() for col in df.columns]
        if not df.empty:
            if date_col and date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df[df[date_col].notna()]
                df = df[df[date_col].dt.date >= (datetime.now().date() - timedelta(days=30))]
            if not df.empty:
                st.markdown(f"### 📋 Recent `{tab_name}`")
                st.dataframe(df.sort_values(by=date_col, ascending=False) if date_col and date_col in df.columns else df)
            else:
                st.info(f"No recent data in `{tab_name}`.")
        else:
            st.info(f"No data found in `{tab_name}`.")
    except Exception as e:
        st.error(f"Error loading `{tab_name}`: {e}")
