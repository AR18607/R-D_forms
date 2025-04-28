import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS_FILE = "rnd-form-sheets-b47d625d6fd9.json"

# Table Tab Names
TAB_SOLUTION_ID = "Solution ID Tbl"
TAB_SOLUTION_PREP = "Solution Prep Data Tbl"
TAB_COMBINED_SOLUTION = "Combined Solution Tbl"

# ------------------ CONNECTION FUNCTIONS ------------------

def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    import json
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
    records = worksheet.col_values(1)[1:]  # Skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

# ------------------ STREAMLIT FORM ------------------

st.title("🧪 Solution Management Form (3 Tabs, Dynamic IDs)")

# Connect
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Tabs
solution_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_ID, ["Solution ID", "Type", "Expired", "Consumed"])
prep_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_PREP, [
    "Solution Prep ID", "Solution ID (FK)", "Desired Solution Concentration", "Desired Final Volume",
    "Solvent", "Solvent Lot Number", "Solvent Weight Measured (g)", "Polymer", "Polymer starting concentration",
    "Polymer Lot Number", "Polymer Weight Measured (g)", "Prep Date", "Initials", "Notes",
    "C-Solution Concentration", "C-Label for jar"
])
combined_sheet = get_or_create_tab(spreadsheet, TAB_COMBINED_SOLUTION, [
    "Combined Solution ID", "Solution ID (FK)", "Solution Prep ID (FK)", "Solution Mass",
    "Date", "Initials", "Notes", "C-Label for jar"
])

# Fetch Existing Solution IDs and Prep IDs
existing_solution_ids = solution_sheet.col_values(1)[1:]
existing_prep_ids = prep_sheet.col_values(1)[1:]

# Form Sections
with st.form("full_solution_form"):

    st.subheader("🔹 Solution ID Entry")
    solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])

    st.subheader("🔹 Solution Prep Data Entry")
    prep_id = get_last_id(prep_sheet, "PREP")
    st.markdown(f"**Auto-generated Prep ID:** `{prep_id}`")
    if existing_solution_ids:
        solution_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids)
    else:
        solution_fk = st.text_input("Solution ID (FK)", solution_id)  # fallback new ID

    desired_conc = st.number_input("Desired Solution Concentration (%)", format="%.2f")
    final_volume = st.number_input("Desired Final Volume", format="%.1f")
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'])
    solvent_lot = st.text_input("Solvent Lot Number")
    solvent_weight = st.number_input("Solvent Weight Measured (g)", format="%.2f")
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'])
    polymer_start_conc = st.number_input("Polymer Starting Concentration (%)", format="%.2f")
    polymer_lot = st.text_input("Polymer Lot Number")
    polymer_weight = st.number_input("Polymer Weight Measured (g)", format="%.2f")
    prep_date = st.date_input("Preparation Date")
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    c_sol_conc = st.number_input("C-Solution Concentration", format="%.2f")
    c_label_jar = st.text_input("C-Label for Jar")

    st.subheader("🔹 Combined Solution Entry")
    combined_id = get_last_id(combined_sheet, "COMB")
    st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
    if existing_solution_ids:
        combined_solution_fk = st.selectbox("Select Solution ID (for Combined)", existing_solution_ids, key="sol_comb")
    else:
        combined_solution_fk = st.text_input("Solution ID (Combined FK)", solution_id)

    if existing_prep_ids:
        combined_prep_fk = st.selectbox("Select Prep ID (for Combined)", existing_prep_ids)
    else:
        combined_prep_fk = st.text_input("Solution Prep ID (Combined FK)", prep_id)

    solution_mass = st.number_input("Solution Mass (g)", format="%.2f")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Combined Initials")
    combined_notes = st.text_area("Combined Notes")
    combined_label_jar = st.text_input("C-Label for Jar (Combined)")

    submit_button = st.form_submit_button("🚀 Submit All Entries")

# ------------------ SAVE DATA ------------------

if submit_button:
    try:
        # Insert Solution ID entry
        solution_sheet.append_row([solution_id, solution_type, expired, consumed])

        # Insert Solution Prep entry
        prep_sheet.append_row([
            prep_id, solution_fk, desired_conc, final_volume, solvent, solvent_lot,
            solvent_weight, polymer, polymer_start_conc, polymer_lot, polymer_weight,
            str(prep_date), initials, notes, c_sol_conc, c_label_jar
        ])

        # Insert Combined Solution entry
        combined_sheet.append_row([
            combined_id, combined_solution_fk, combined_prep_fk, solution_mass,
            str(combined_date), combined_initials, combined_notes, combined_label_jar
        ])

        st.success("✅ Data successfully saved across all 3 tables!")

    except Exception as e:
        st.error(f"❌ Error while saving: {e}")

