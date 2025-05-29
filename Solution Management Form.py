# --- Import Required Libraries ---
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import time
# --- Configuration ---
SPREADSHEET_KEY = "1uPdUWiiwMdJCYJaxZ5TneFa9h6tbSrs327BVLT5GVPY"
SOLUTION_ID_HEADERS = ["Solution ID", "Type", "Expired", "Consumed"]
PREP_HEADERS = [
    "Solution Prep ID", "Solution ID (FK)", "Desired Solution Concentration", "Desired Final Volume",
    "Solvent", "Solvent Lot Number", "Solvent Weight Measured (g)", "Polymer",
    "Polymer starting concentration", "Polymer Lot Number", "Polymer Weight Measured (g)",
    "Prep Date", "Initials", "Notes", "C-Solution Concentration", "C-Label for jar"
]
COMBINED_HEADERS = [
    "Combined Solution ID", "Solution ID A", "Solution ID B",
    "Solution Mass A", "Solution Mass B", "Date", "Initials", "Notes"
]
# --- Utility Functions ---
@st.cache_resource(ttl=600)
def connect_google_sheet(sheet_key):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_key)
def retry_open_worksheet(spreadsheet, tab_name, retries=3, wait=2):
    for i in range(retries):
        try:
            return spreadsheet.worksheet(tab_name)
        except gspread.exceptions.APIError as e:
            if i < retries - 1:
                time.sleep(wait)
            else:
                st.error(f":rotating_light: API Error while accessing tab `{tab_name}`: {str(e)}")
                st.stop()
def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = retry_open_worksheet(spreadsheet, tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet
@st.cache_data(ttl=120)
def cached_col_values(sheet_key, tab_name, col=1):
    spreadsheet = connect_google_sheet(sheet_key)
    worksheet = retry_open_worksheet(spreadsheet, tab_name)
    return worksheet.col_values(col)[1:]
@st.cache_data(ttl=120)
def cached_get_all_records(sheet_key, tab_name):
    spreadsheet = connect_google_sheet(sheet_key)
    worksheet = retry_open_worksheet(spreadsheet, tab_name)
    return worksheet.get_all_records()
# Uncached function for generating IDs
def get_last_id_from_records(records, id_prefix):
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"
def safe_get(record, key, default=""):
    if isinstance(record, dict):
        for k, v in record.items():
            if k.strip().lower() == key.strip().lower():
                return v
    return default
def parse_date(date_val):
    if isinstance(date_val, datetime):
        return date_val
    elif isinstance(date_val, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_val.strip(), fmt)
            except:
                continue
    return None
# --- Setup ---
spreadsheet = connect_google_sheet(SPREADSHEET_KEY)
solution_sheet = get_or_create_tab(spreadsheet, "Solution ID Tbl", SOLUTION_ID_HEADERS)
prep_sheet = get_or_create_tab(spreadsheet, "Solution Prep Data Tbl", PREP_HEADERS)
combined_sheet = get_or_create_tab(spreadsheet, "Combined Solution Tbl", COMBINED_HEADERS)
# --- Form Title ---
st.markdown("# :page_facing_up: **Solution Management Form**")
st.markdown("Manage creation, preparation, and combination of solutions.")
existing_solution_ids = cached_col_values(SPREADSHEET_KEY, "Solution ID Tbl")
# --- Solution ID Form ---
st.markdown("## :small_blue_diamond: Solution ID Entry")
with st.form("solution_id_form"):
    solution_id = get_last_id_from_records(existing_solution_ids, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])
    submit_solution = st.form_submit_button("Submit New Solution ID")
if submit_solution:
    solution_sheet.append_row([solution_id, solution_type, expired, consumed])
    st.success(":white_check_mark: Solution ID saved!")
st.divider()
# --- Solution Prep Form ---
st.markdown("## :small_blue_diamond: Solution Prep Data Entry")
selected_solution_fk = st.selectbox("Select Solution ID", options=existing_solution_ids, key="prep_solution_fk")
prep_entries = cached_get_all_records(SPREADSHEET_KEY, "Solution Prep Data Tbl")
existing_record = next((r for r in prep_entries if r.get("Solution ID (FK)", "") == selected_solution_fk), None)
if existing_record:
    st.info(":large_yellow_circle: Existing prep entry found. Fields prefilled for update.")
else:
    st.info(":large_green_circle: No prep entry found. Enter new details.")
with st.form("prep_data_form"):
    prep_id = safe_get(existing_record, "Solution Prep ID", get_last_id_from_records(
        [r["Solution Prep ID"] for r in prep_entries if "Solution Prep ID" in r], "PREP"
    ))
    st.markdown(f"**Prep ID:** `{prep_id}`")
    desired_conc = st.number_input(
        "Desired Solution Concentration (%)",
        value=float(safe_get(existing_record, "Desired Solution Concentration", 0.0)),
        format="%.2f"
    )
    final_volume = st.number_input(
        "Desired Final Volume",
        value=float(safe_get(existing_record, "Desired Final Volume", 0.0)),
        format="%.1f"
    )
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'],
        index=['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(safe_get(existing_record, "Solvent", "IPA")) if existing_record else 0
    )
    solvent_lot = st.text_input("Solvent Lot Number", value=safe_get(existing_record, "Solvent Lot Number", ""))
    solvent_weight = st.number_input("Solvent Weight Measured (g)",
        value=float(safe_get(existing_record, "Solvent Weight Measured (g)", 0.0)),
        format="%.2f"
    )
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'],
        index=['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(safe_get(existing_record, "Polymer", "CMS-72")) if existing_record else 0
    )
    polymer_conc = st.number_input("Polymer starting concentration (%)",
        value=float(safe_get(existing_record, "Polymer starting concentration", 0.0)),
        format="%.2f"
    )
    polymer_lot = st.text_input("Polymer Lot Number", value=safe_get(existing_record, "Polymer Lot Number", ""))
    polymer_weight = st.number_input("Polymer Weight Measured (g)",
        value=float(safe_get(existing_record, "Polymer Weight Measured (g)", 0.0)),
        format="%.2f"
    )
    prep_date_str = safe_get(existing_record, "Prep Date")
    try:
        prep_date = datetime.strptime(prep_date_str, "%Y-%m-%d").date() if prep_date_str else datetime.today().date()
    except:
        prep_date = datetime.today().date()
    prep_date = st.date_input("Prep Date", value=prep_date)
    initials = st.text_input("Initials", value=safe_get(existing_record, "Initials", ""))
    notes = st.text_area("Notes", value=safe_get(existing_record, "Notes", ""))
    c_sol_conc = st.number_input("C-Solution Concentration",
        value=float(safe_get(existing_record, "C-Solution Concentration", 0.0)),
        format="%.2f"
    )
    c_label_jar = st.text_input("C-Label for jar", value=safe_get(existing_record, "C-Label for jar", ""))
    submit_prep = st.form_submit_button("Submit/Update Prep Details")
if submit_prep:
    data = [
        prep_id, selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot,
        solvent_weight, polymer, polymer_conc, polymer_lot, polymer_weight, str(prep_date),
        initials, notes, c_sol_conc, c_label_jar
    ]
    try:
        if existing_record:
            cell = prep_sheet.find(selected_solution_fk)
            row_number = cell.row
            prep_sheet.update(f"A{row_number}:P{row_number}", [data])
            st.success(":white_check_mark: Prep Data updated!")
        else:
            prep_sheet.append_row(data)
            st.success(":white_check_mark: Prep Data submitted!")
    except Exception as e:
        st.error(f":x: Error while writing to Google Sheet: {e}")
# --- Combined Solution Form ---
st.markdown("## :small_blue_diamond: Combined Solution Entry")
with st.form("combined_solution_form"):
    combined_id = get_last_id_from_records(cached_col_values(SPREADSHEET_KEY, "Combined Solution Tbl"), "COMB")
    st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
    solution_id_a = st.selectbox("Solution ID A", options=existing_solution_ids, key="comb_a")
    solution_id_b = st.selectbox("Solution ID B", options=existing_solution_ids, key="comb_b")
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Initials")
    combined_notes = st.text_area("Notes")
    submit_combined = st.form_submit_button("Submit Combined Solution Details")
if submit_combined:
    combined_sheet.append_row([
        combined_id, solution_id_a, solution_id_b,
        solution_mass_a, solution_mass_b, str(combined_date),
        combined_initials, combined_notes
    ])
    st.success(":white_check_mark: Combined Solution saved!")
# ------------------ 7-DAY FILTERED VIEW USING PREP DATE ------------------
st.markdown("## 📅 Last 7 Days Data Preview (Based on Prep Date)")

# Step 1: Build reference dictionary from Solution Prep Data Tbl
prep_records = prep_sheet.get_all_records()
recent_solution_ids = set()
recent_prep_ids = []
today = datetime.today()

for rec in prep_records:
    parsed = parse_date(rec.get("Prep Date", "").strip())
    if parsed and parsed >= today - timedelta(days=7):
        recent_prep_ids.append(rec)
        recent_solution_ids.add(rec.get("Solution ID (FK)", "").strip())

# Step 2: Solution ID Table - show only those with IDs in recent_prep_ids
st.markdown("### 📘 Solution ID Table (Filtered by Recent Prep)")
solution_records = solution_sheet.get_all_records()
filtered_solution_ids = [rec for rec in solution_records if rec.get("Solution ID", "").strip() in recent_solution_ids]

if filtered_solution_ids:
    st.dataframe(pd.DataFrame(filtered_solution_ids))
else:
    st.write("No recent Solution ID records based on prep activity.")

# Step 3: Solution Prep Data Table - directly show recent entries
st.markdown("### 🧪 Solution Prep Data (Last 7 Days Only)")
if recent_prep_ids:
    st.dataframe(pd.DataFrame(recent_prep_ids))
else:
    st.write("No Solution Prep records in the last 7 days.")

# Step 4: Combined Solution Table - filter if A or B used recently
st.markdown("### 🧪 Combined Solution Data (Using Recently Prepped IDs)")
combined_records = combined_sheet.get_all_records()
recent_combined = [
    rec for rec in combined_records
    if rec.get("Solution ID A", "").strip() in recent_solution_ids or
       rec.get("Solution ID B", "").strip() in recent_solution_ids
]

if recent_combined:
    st.dataframe(pd.DataFrame(recent_combined))
else:
    st.write("No Combined Solution records linked to recent prep entries.")
