import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

# Tab Names
TAB_MODULE = "Module Tbl"
TAB_LEAK = "Leak Test Tbl"
TAB_FAILURES = "Module Failures Tbl"

# Prevent accidental form submit on Enter
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# --- Google Sheet Functions ---
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
        # Check headers. Only re-insert if misaligned.
        first_row = worksheet.row_values(1)
        if [h.strip() for h in first_row] != [h.strip() for h in headers]:
            worksheet.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_col_values(sheet_name, col_index):
    sheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(sheet_name)
    return worksheet.col_values(col_index)

def get_all_records(sheet_name):
    sheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(sheet_name)
    return worksheet.get_all_records()

def get_last_id(sheet_name, prefix):
    records = get_col_values(sheet_name, 1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix) and r.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

# --- Start Streamlit App ---
st.title("🛠 Module Management Form")

# --- Connect & Show Tabs (for debug!) ---
try:
    spreadsheet = cached_connect_google_sheet(GOOGLE_SHEET_NAME)
    tab_names = [ws.title for ws in spreadsheet.worksheets()]
    #st.info(f"Tabs found: {tab_names}")
except Exception as e:
    st.error(f"Failed to load sheet: {e}")
    st.stop()

# --- Create/Check Tabs with the proper headers ---
MODULE_HEADERS = ["Module ID", "Module Type", "Label", "Notes"]
FAILURE_HEADERS = [
    "Module Failure ID", "Module ID", "Description of Failure", "Autopsy", "Autopsy Notes",
    "Microscopy", "Microscopy Notes", "Failure Mode", "Operator Initials", "Date", "Label"
]
LEAK_HEADERS = [
    "Leak Test ID", "Module ID", "Module Type", "End", "Leak Test Type", "Leak Location",
    "Repaired", "Operator Initials", "Notes", "Date/Time"
]
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, MODULE_HEADERS)
leak_sheet = get_or_create_tab(spreadsheet, TAB_LEAK, LEAK_HEADERS)
failure_sheet = get_or_create_tab(spreadsheet, TAB_FAILURES, FAILURE_HEADERS)

# --- Load DataFrames ---
try:
    module_records = get_all_records(TAB_MODULE)
    existing_modules_df = pd.DataFrame(module_records)
    if not existing_modules_df.empty:
        existing_modules_df.fillna("", inplace=True)
    failures_df = pd.DataFrame(get_all_records(TAB_FAILURES))
    leak_df = pd.DataFrame(get_all_records(TAB_LEAK))
except Exception as e:
    st.error(f"Error loading table data: {e}")
    st.stop()

# --- Prepare Module Option with Type & Label (not Notes) ---
def module_label(row):
    return f"{row['Module ID']} / {row.get('Module Type', '')} / {row.get('Label', '')}".replace(' /  / ', ' / ')

if not existing_modules_df.empty:
    module_options = existing_modules_df.apply(module_label, axis=1).tolist()
    module_id_set = set(existing_modules_df["Module ID"].tolist())
else:
    module_options = []
    module_id_set = set()

# --- MODULE ENTRY FORM ---
st.subheader("🔹 Module Entry")
with st.form("module_entry_form", clear_on_submit=True):
    module_id = get_last_id(TAB_MODULE, "MOD")
    st.markdown(f"**Auto-generated Module ID:** `{module_id}`")
    module_type = st.selectbox("Module Type", ["Wound", "Mini"])
    label = st.text_input("Label (e.g. batch, serial #, etc.)")
    module_notes = st.text_area("Notes")
    if st.form_submit_button("🚀 Submit Module"):
        module_sheet.append_row([module_id, module_type, label, module_notes])
        st.success(f"✅ Module {module_id} saved successfully!")

# --- MODULE FAILURE FORM ---
st.subheader("🔹 Module Failure Entry")
# Only show unused (not yet failed) module IDs in dropdown
used_module_ids = set(failures_df["Module ID"].tolist()) if not failures_df.empty and "Module ID" in failures_df else set()
unused_module_options = [opt for opt in module_options if opt.split(" / ")[0] not in used_module_ids]
with st.form("failure_entry_form", clear_on_submit=True):
    failure_id = get_last_id(TAB_FAILURES, "FAIL")
    st.markdown(f"**Auto-generated Failure ID:** `{failure_id}`")
    failure_module_fk = st.selectbox("Module ID (unique)", unused_module_options)
    description = st.text_area("Description of Failure")
    autopsy = st.selectbox("Autopsy Done?", ["Yes", "No"])
    autopsy_notes = st.text_area("Autopsy Notes")
    microscopy = st.selectbox("Microscopy Type", ["Classical", "SEM", "None"])
    microscopy_notes = st.text_area("Microscopy Notes")
    failure_mode = st.text_input("Failure Mode")
    operator_initials = st.text_input("Operator Initials")
    failure_date = st.date_input("Failure Date")
    label_fail = st.selectbox(
        "Label (select to view previous)", 
        sorted(existing_modules_df["Label"].unique().tolist()) if not existing_modules_df.empty else [""]
    )
    if label_fail:
        prev_details = existing_modules_df[existing_modules_df["Label"] == label_fail]
        if not prev_details.empty:
            st.markdown("**Previous details for this Label:**")
            st.table(prev_details)
    if st.form_submit_button("🚨 Submit Failure Entry"):
        mod_id = failure_module_fk.split(' / ')[0]
        failure_sheet.append_row([
            failure_id, mod_id, description, autopsy, autopsy_notes,
            microscopy, microscopy_notes, failure_mode, operator_initials,
            str(failure_date), label_fail
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
        mod_type = module_selection.split(' / ')[1] if len(module_selection.split(' / ')) > 1 else ""
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for point in st.session_state.leak_points:
            leak_sheet.append_row([leak_id, mod_id, mod_type, point["End"], leak_test_type,
                                   point["Leak Location"], point["Repaired"], operator_initials,
                                   point["Notes"], date_now])
        st.success(f"✅ Leak points saved under Leak ID {leak_id}")
        st.session_state.leak_points = []

# --- 30-DAYS DATA REVIEW ---
st.subheader("📅 Records (Last 30 Days)")
for tab_name, date_col in [(TAB_MODULE, None), (TAB_LEAK, "Date/Time"), (TAB_FAILURES, "Date")]:
    try:
        df = pd.DataFrame(get_all_records(tab_name))
        df.columns = [col.strip() for col in df.columns]
        if not df.empty:
            if date_col:
                date_col_clean = date_col.strip()
                if date_col_clean in df.columns:
                    df[date_col_clean] = pd.to_datetime(df[date_col_clean], errors="coerce")
                    df = df[df[date_col_clean].notna()]
                    df = df[df[date_col_clean].dt.date >= (datetime.now().date() - timedelta(days=30))]
                else:
                    st.warning(f"⚠️ Column '{date_col}' not found in `{tab_name}`.")
                    continue
            if not df.empty:
                st.markdown(f"### 📋 Recent `{tab_name}`")
                st.dataframe(df.sort_values(by=date_col_clean, ascending=False) if date_col else df)
            else:
                st.info(f"No recent data in `{tab_name}`.")
        else:
            st.info(f"No data found in `{tab_name}`.")
    except Exception as e:
        st.error(f"Error loading `{tab_name}`: {e}")
