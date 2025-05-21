# --- Import Required Libraries ---
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

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


def connect_google_sheet(sheet_key):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_key)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

# --- Setup ---
spreadsheet = connect_google_sheet(SPREADSHEET_KEY)
solution_sheet = get_or_create_tab(spreadsheet, "Solution ID Tbl", SOLUTION_ID_HEADERS)
prep_sheet = get_or_create_tab(spreadsheet, "Solution Prep Data Tbl", PREP_HEADERS)
combined_sheet = get_or_create_tab(spreadsheet, "Combined Solution Tbl", COMBINED_HEADERS)
existing_solution_ids = solution_sheet.col_values(1)[1:]

# --- Solution ID Form ---
st.markdown("## 🔹 Solution ID Entry")
with st.form("solution_id_form"):
    solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])
    submit_solution = st.form_submit_button("Submit New Solution ID")

if submit_solution:
    solution_sheet.append_row([solution_id, solution_type, expired, consumed])
    st.success("✅ Solution ID saved!")

st.divider()

# --- Solution Prep Form ---
st.markdown("## 🔹 Solution Prep Data Entry")
selected_solution_fk = st.selectbox("Select Solution ID", options=existing_solution_ids, key="prep_solution_fk")
prep_entries = prep_sheet.get_all_records()
existing_record = next((r for r in prep_entries if r.get("Solution ID (FK)", "") == selected_solution_fk), None)

if existing_record:
    st.info("🟡 Existing prep entry found. Fields prefilled for update.")
else:
    st.info("🟢 No prep entry found. Enter new details.")

with st.form("prep_data_form"):
    prep_id = safe_get(existing_record, "Solution Prep ID", get_last_id(prep_sheet, "PREP")) if existing_record else get_last_id(prep_sheet, "PREP")
    st.markdown(f"**Prep ID:** `{prep_id}`")

    def get_float(key): return float(safe_get(existing_record, key, 0.0)) if existing_record else 0.0

    desired_conc = st.number_input("Desired Solution Concentration (%)", value=get_float("Desired Solution Concentration"), format="%.2f")
    final_volume = st.number_input("Desired Final Volume", value=get_float("Desired Final Volume"), format="%.1f")
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'])
    solvent_lot = st.text_input("Solvent Lot Number", value=safe_get(existing_record, "Solvent Lot Number", "") if existing_record else "")
    solvent_weight = st.number_input("Solvent Weight Measured (g)", value=get_float("Solvent Weight Measured (g)"), format="%.2f")
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'])
    polymer_conc = st.number_input("Polymer starting concentration (%)", value=get_float("Polymer starting concentration"), format="%.2f")
    polymer_lot = st.text_input("Polymer Lot Number", value=safe_get(existing_record, "Polymer Lot Number", "") if existing_record else "")
    polymer_weight = st.number_input("Polymer Weight Measured (g)", value=get_float("Polymer Weight Measured (g)"), format="%.2f")
    prep_date = st.date_input("Prep Date", value=parse_date(safe_get(existing_record, "Prep Date")) or datetime.today())
    initials = st.text_input("Initials", value=safe_get(existing_record, "Initials", "") if existing_record else "")
    notes = st.text_area("Notes", value=safe_get(existing_record, "Notes", "") if existing_record else "")
    c_sol_conc = st.number_input("C-Solution Concentration", value=get_float("C-Solution Concentration"), format="%.2f")
    c_label_jar = st.text_input("C-Label for jar", value=safe_get(existing_record, "C-Label for jar", "") if existing_record else "")

    submit_prep = st.form_submit_button("Submit/Update Prep Details")

if submit_prep:
    data = [
        prep_id, selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot,
        solvent_weight, polymer, polymer_conc, polymer_lot, polymer_weight, str(prep_date),
        initials, notes, c_sol_conc, c_label_jar
    ]
    if existing_record:
        cell = prep_sheet.find(selected_solution_fk)
        row_number = cell.row
        prep_sheet.update(f"A{row_number}:P{row_number}", [data])
        st.success("✅ Prep Data updated!")
    else:
        prep_sheet.append_row(data)
        st.success("✅ Prep Data submitted!")

st.divider()

# --- Combined Solution Form ---
st.markdown("## 🔹 Combined Solution Entry")
with st.form("combined_solution_form"):
    combined_id = get_last_id(combined_sheet, "COMB")
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
    st.success("✅ Combined Solution saved!")

st.divider()

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
