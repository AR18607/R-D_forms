import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

# ------------------ CONFIGURATION ------------------
SPREADSHEET_KEY = "1uPdUWiiwMdJCYJaxZ5TneFa9h6tbSrs327BVLT5GVPY"

# Headers for the tables
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

# ------------------ UTILITY FUNCTION ------------------

def safe_get(record, key, default=""):
    """
    Return value from record for a key by matching case-insensitively and ignoring extra spaces.
    """
    if isinstance(record, dict):
        for k, v in record.items():
            if k.strip().lower() == key.strip().lower():
                return v
    return default

# ------------------ GOOGLE SHEET CONNECTION ------------------

def connect_google_sheet(sheet_key):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
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
    records = worksheet.col_values(1)[1:]  # Skip header row
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

# ------------------ GOOGLE SHEET SETUP ------------------

spreadsheet = connect_google_sheet(SPREADSHEET_KEY)

solution_sheet = get_or_create_tab(spreadsheet, "Solution ID Tbl", SOLUTION_ID_HEADERS)
prep_sheet = get_or_create_tab(spreadsheet, "Solution Prep Data Tbl", PREP_HEADERS)
combined_sheet = get_or_create_tab(spreadsheet, "Combined Solution Tbl", COMBINED_HEADERS)

existing_solution_ids = solution_sheet.col_values(1)[1:]

# ------------------ SOLUTION ID FORM ------------------

with st.form("solution_id_form"):
    st.subheader("🔹 Solution ID Entry")
    solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])
    submit_solution = st.form_submit_button("Submit Solution ID")

if submit_solution:
    solution_sheet.append_row([solution_id, solution_type, expired, consumed])
    st.success("✅ Solution ID saved!")

# ------------------ SOLUTION PREP DATA ENTRY ------------------

st.subheader("🔹 Solution Prep Data Entry")
# Let the user select a Solution ID (from solution_sheet) as foreign key
selected_solution_fk = st.selectbox("Select Solution ID for Prep Entry", options=existing_solution_ids, key="prep_solution_fk")

# Retrieve existing prep entries for lookup
prep_entries = prep_sheet.get_all_records()  # list of dicts keyed by header
existing_record = None
for record in prep_entries:
    if record.get("Solution ID (FK)", "") == selected_solution_fk:
        existing_record = record
        break

if existing_record:
    st.info("Existing prep entry found for the selected Solution ID. The fields are prefilled for an update.")
else:
    st.info("No existing prep entry found; please enter new details.")

with st.form("prep_data_form"):
    # If a record exists, prefill values; otherwise, use defaults.
    if existing_record:
        prep_id = safe_get(existing_record, "Solution Prep ID", get_last_id(prep_sheet, "PREP"))
        try:
            default_desired_conc = float(safe_get(existing_record, "Desired Solution Concentration", 0.0))
        except:
            default_desired_conc = 0.0
        try:
            default_final_volume = float(safe_get(existing_record, "Desired Final Volume", 0.0))
        except:
            default_final_volume = 0.0
        default_solvent = safe_get(existing_record, "Solvent", "IPA")
        default_solvent_lot = safe_get(existing_record, "Solvent Lot Number", "")
        try:
            default_solvent_weight = float(safe_get(existing_record, "Solvent Weight Measured (g)", 0.0))
        except:
            default_solvent_weight = 0.0
        default_polymer = safe_get(existing_record, "Polymer", "CMS-72")
        try:
            default_polymer_conc = float(safe_get(existing_record, "Polymer starting concentration", 0.0))
        except:
            default_polymer_conc = 0.0
        default_polymer_lot = safe_get(existing_record, "Polymer Lot Number", "")
        try:
            default_polymer_weight = float(safe_get(existing_record, "Polymer Weight Measured (g)", 0.0))
        except:
            default_polymer_weight = 0.0
        try:
            default_prep_date = datetime.strptime(safe_get(existing_record, "Prep Date", datetime.today().strftime("%Y-%m-%d")), "%Y-%m-%d").date()
        except:
            default_prep_date = datetime.today().date()
        default_initials = safe_get(existing_record, "Initials", "")
        default_notes = safe_get(existing_record, "Notes", "")
        try:
            default_c_sol_conc = float(safe_get(existing_record, "C-Solution Concentration", 0.0))
        except:
            default_c_sol_conc = 0.0
        default_c_label_jar = safe_get(existing_record, "C-Label for jar", "")
    else:
        prep_id = get_last_id(prep_sheet, "PREP")
        default_desired_conc = 0.0
        default_final_volume = 0.0
        default_solvent = "IPA"
        default_solvent_lot = ""
        default_solvent_weight = 0.0
        default_polymer = "CMS-72"
        default_polymer_conc = 0.0
        default_polymer_lot = ""
        default_polymer_weight = 0.0
        default_prep_date = datetime.today().date()
        default_initials = ""
        default_notes = ""
        default_c_sol_conc = 0.0
        default_c_label_jar = ""
    
    st.markdown(f"**Prep ID:** `{prep_id}`")
    desired_conc = st.number_input("Desired Solution Concentration (%)", value=default_desired_conc, format="%.2f")
    final_volume = st.number_input("Desired Final Volume", value=default_final_volume, format="%.1f")
    solvent = st.selectbox(
        "Solvent",
        ['IPA', 'EtOH', 'Heptane', 'Novec 7300'],
        index=(['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(default_solvent)
               if default_solvent in ['IPA', 'EtOH', 'Heptane', 'Novec 7300'] else 0)
    )
    solvent_lot = st.text_input("Solvent Lot Number", value=default_solvent_lot)
    solvent_weight = st.number_input("Solvent Weight Measured (g)", value=default_solvent_weight, format="%.2f")
    polymer = st.selectbox(
        "Polymer",
        ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'],
        index=(['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(default_polymer)
               if default_polymer in ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'] else 0)
    )
    polymer_conc = st.number_input("Polymer starting concentration (%)", value=default_polymer_conc, format="%.2f")
    polymer_lot = st.text_input("Polymer Lot Number", value=default_polymer_lot)
    polymer_weight = st.number_input("Polymer Weight Measured (g)", value=default_polymer_weight, format="%.2f")
    prep_date = st.date_input("Prep Date", value=default_prep_date)
    initials = st.text_input("Initials", value=default_initials)
    notes = st.text_area("Notes", value=default_notes)
    
    # Two additional fields per header definition:
    c_sol_conc = st.number_input("C-Solution Concentration", value=default_c_sol_conc, format="%.2f")
    c_label_jar = st.text_input("C-Label for jar", value=default_c_label_jar)
    
    submit_prep = st.form_submit_button("Update Prep Entry" if existing_record else "Submit Prep Entry")

if submit_prep:
    data = [
        prep_id,
        selected_solution_fk,
        desired_conc,
        final_volume,
        solvent,
        solvent_lot,
        solvent_weight,
        polymer,
        polymer_conc,
        polymer_lot,
        polymer_weight,
        str(prep_date),
        initials,
        notes,
        c_sol_conc,
        c_label_jar
    ]
    if existing_record:
        # Locate the row for the selected solution id and update that row.
        cell = prep_sheet.find(selected_solution_fk)
        row_number = cell.row
        prep_sheet.update(f"A{row_number}:P{row_number}", [data])
        st.success("✅ Prep Data updated!")
    else:
        prep_sheet.append_row(data)
        st.success("✅ Prep Data submitted!")

# ------------------ COMBINED SOLUTION ENTRY ------------------

with st.form("combined_solution_form"):
    st.subheader("🔹 Combined Solution Entry")
    combined_id = get_last_id(combined_sheet, "COMB")
    st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
    solution_id_a = st.selectbox("Solution ID A", options=existing_solution_ids, key="comb_solution_a")
    solution_id_b = st.selectbox("Solution ID B", options=existing_solution_ids, key="comb_solution_b")
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Initials")
    combined_notes = st.text_area("Notes")
    submit_combined = st.form_submit_button("Submit Combined Solution")

if submit_combined:
    combined_sheet.append_row([
        combined_id,
        solution_id_a,
        solution_id_b,
        solution_mass_a,
        solution_mass_b,
        str(combined_date),
        combined_initials,
        combined_notes
    ])
    st.success("✅ Combined Solution saved!")
