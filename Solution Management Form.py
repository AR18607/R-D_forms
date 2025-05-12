import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"

# Table Tab Names
TAB_SOLUTION_ID = "Solution ID Tbl"
TAB_SOLUTION_PREP = "Solution Prep Data Tbl"
TAB_COMBINED_SOLUTION = "Combined Solution Tbl"

# ------------------ CONNECTION FUNCTIONS ------------------

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
    records = worksheet.col_values(1)[1:]  # Skip header row
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

# ------------------ GOOGLE SHEET SETUP ------------------

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

solution_sheet = get_or_create_tab(
    spreadsheet, 
    TAB_SOLUTION_ID, 
    ["Solution ID", "Type", "Expired", "Consumed"]
)

prep_sheet = get_or_create_tab(
    spreadsheet, 
    TAB_SOLUTION_PREP, [
        "Solution Prep ID", "Solution ID (FK)", "Desired Concentration", "Final Volume",
        "Solvent", "Solvent Lot", "Solvent Weight", "Polymer",
        "Polymer Concentration", "Polymer Lot", "Polymer Weight",
        "Prep Date", "Initials", "Notes"
    ]
)

combined_sheet = get_or_create_tab(
    spreadsheet, 
    TAB_COMBINED_SOLUTION, [
        "Combined Solution ID", "Solution ID A", "Solution ID B",
        "Solution Mass A", "Solution Mass B", "Date", "Initials", "Notes"
    ]
)

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
# Let the user select a solution (from the solution sheet) as foreign key
selected_solution_fk = st.selectbox("Select Solution ID for Prep Entry", options=existing_solution_ids, key="prep_solution_fk")

# Retrieve all prep entries for lookup
prep_entries = prep_sheet.get_all_records()  # List of dictionaries keyed by header name
existing_record = None
for record in prep_entries:
    if record["Solution ID (FK)"] == selected_solution_fk:
        existing_record = record
        break

if existing_record:
    st.info("Existing prep entry found for the selected Solution ID. Fields are prefilled for update.")
else:
    st.info("No existing prep entry found; please enter new details.")

with st.form("prep_data_form"):
    # Use existing values if found; otherwise, set to defaults
    if existing_record:
        prep_id = existing_record["Solution Prep ID"]
        try:
            default_desired_conc = float(existing_record["Desired Concentration"])
        except:
            default_desired_conc = 0.0
        try:
            default_final_volume = float(existing_record["Final Volume"])
        except:
            default_final_volume = 0.0
        default_solvent = existing_record["Solvent"] if existing_record["Solvent"] else "IPA"
        default_solvent_lot = existing_record["Solvent Lot"] if existing_record["Solvent Lot"] else ""
        try:
            default_solvent_weight = float(existing_record["Solvent Weight"])
        except:
            default_solvent_weight = 0.0
        default_polymer = existing_record["Polymer"] if existing_record["Polymer"] else "CMS-72"
        try:
            default_polymer_conc = float(existing_record["Polymer Concentration"])
        except:
            default_polymer_conc = 0.0
        default_polymer_lot = existing_record["Polymer Lot"] if existing_record["Polymer Lot"] else ""
        try:
            default_polymer_weight = float(existing_record["Polymer Weight"])
        except:
            default_polymer_weight = 0.0
        try:
            default_prep_date = datetime.strptime(existing_record["Prep Date"], "%Y-%m-%d").date()
        except:
            default_prep_date = datetime.today().date()
        default_initials = existing_record["Initials"] if existing_record["Initials"] else ""
        default_notes = existing_record["Notes"] if existing_record["Notes"] else ""
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
    
    st.markdown(f"**Prep ID:** `{prep_id}`")
    desired_conc = st.number_input("Desired Concentration (%)", value=default_desired_conc, format="%.2f")
    final_volume = st.number_input("Final Volume", value=default_final_volume, format="%.1f")
    solvent = st.selectbox(
        "Solvent",
        ['IPA', 'EtOH', 'Heptane', 'Novec 7300'],
        index=(['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(default_solvent)
               if default_solvent in ['IPA', 'EtOH', 'Heptane', 'Novec 7300'] else 0)
    )
    solvent_lot = st.text_input("Solvent Lot", value=default_solvent_lot)
    solvent_weight = st.number_input("Solvent Weight (g)", value=default_solvent_weight, format="%.2f")
    polymer = st.selectbox(
        "Polymer",
        ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'],
        index=(['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(default_polymer)
               if default_polymer in ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'] else 0)
    )
    polymer_conc = st.number_input("Polymer Concentration (%)", value=default_polymer_conc, format="%.2f")
    polymer_lot = st.text_input("Polymer Lot", value=default_polymer_lot)
    polymer_weight = st.number_input("Polymer Weight (g)", value=default_polymer_weight, format="%.2f")
    prep_date = st.date_input("Preparation Date", value=default_prep_date)
    initials = st.text_input("Operator Initials", value=default_initials)
    notes = st.text_area("Notes", value=default_notes)
    
    submit_prep = st.form_submit_button("Update Prep Entry" if existing_record else "Submit Prep Entry")

if submit_prep:
    # Data list to be saved/updated in the prep sheet (order must match the headers)
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
        notes
    ]
    if existing_record:
        # Locate the row for the selected solution id and update that row
        cell = prep_sheet.find(selected_solution_fk)
        row_number = cell.row
        prep_sheet.update(f"A{row_number}:N{row_number}", [data])
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
