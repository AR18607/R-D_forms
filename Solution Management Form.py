import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = st.secrets["gcp_service_account"]

# Table Tab Names
TAB_SOLUTION_ID = "Solution ID Tbl"
TAB_SOLUTION_PREP = "Solution Prep Data Tbl"
TAB_COMBINED_SOLUTION = "Combined Solution Tbl"

# ------------------ CONNECTION FUNCTIONS ------------------

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

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]  # Skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def fetch_column_values(worksheet, col_index=1):
    try:
        values = worksheet.col_values(col_index)[1:]  # Skip header
        return [v for v in values if v]
    except Exception:
        return []

def fetch_row_by_value(worksheet, search_value, col_index=1):
    try:
        cell = worksheet.find(search_value)
        row = worksheet.row_values(cell.row)
        return row
    except:
        return None

# ------------------ MAIN APP ------------------

st.title("🧪 Solution Management Form")

# Connect to Google Sheet
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Worksheets
solution_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_ID, ["Solution ID", "Type", "Expired", "Consumed"])
prep_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_PREP, [
    "Solution Prep ID", "Solution ID (FK)", "Desired Solution Concentration", "Desired Final Volume",
    "Solvent", "Solvent Lot Number", "Solvent Weight Measured (g)", "Polymer", "Polymer starting concentration",
    "Polymer Lot Number", "Polymer Weight Measured (g)", "Prep Date", "Initials", "Notes",
    "C-Solution Concentration", "C-Label for jar"
])
combined_sheet = get_or_create_tab(spreadsheet, TAB_COMBINED_SOLUTION, [
    "Combined Solution ID", "Solution ID A", "Solution ID B", "Solution Mass A",
    "Solution Mass B", "Date", "Initials", "Notes", "C-Label for jar"
])

# Fetch Existing IDs
existing_solution_ids = fetch_column_values(solution_sheet)
existing_prep_ids = fetch_column_values(prep_sheet)

# ------------------ SOLUTION ID FORM ------------------
st.subheader("🔹 Solution ID Entry")
with st.form("solution_id_form"):
    new_solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{new_solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])
    submit_solution_id = st.form_submit_button("Submit Solution ID")

if submit_solution_id:
    try:
        solution_sheet.append_row([new_solution_id, solution_type, expired, consumed])
        st.success(f"✅ Solution ID `{new_solution_id}` added successfully.")
        existing_solution_ids.append(new_solution_id)
    except Exception as e:
        st.error(f"❌ Error while saving Solution ID: {e}")

# ------------------ SOLUTION PREP FORM ------------------
st.subheader("🔹 Solution Prep Data Entry")
with st.form("solution_prep_form"):
    prep_id = get_last_id(prep_sheet, "PREP")
    st.markdown(f"**Auto-generated Prep ID:** `{prep_id}`")
    solution_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids)

    # Check if the selected Solution ID has existing prep data
    existing_prep_data = None
    for row in prep_sheet.get_all_records():
        if row["Solution ID (FK)"] == solution_fk:
            existing_prep_data = row
            break

    if existing_prep_data:
        st.warning("Existing prep data found. Fields are pre-filled for editing.")
        desired_conc = st.number_input("Desired Solution Concentration (%)", value=float(existing_prep_data["Desired Solution Concentration"]), format="%.2f")
        final_volume = st.number_input("Desired Final Volume", value=float(existing_prep_data["Desired Final Volume"]), format="%.1f")
        solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'], index=['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(existing_prep_data["Solvent"]))
        solvent_lot = st.text_input("Solvent Lot Number", value=existing_prep_data["Solvent Lot Number"])
        solvent_weight = st.number_input("Solvent Weight Measured (g)", value=float(existing_prep_data["Solvent Weight Measured (g)"]), format="%.2f")
        polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'], index=['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(existing_prep_data["Polymer"]))
        polymer_start_conc = st.number_input("Polymer Starting Concentration (%)", value=float(existing_prep_data["Polymer starting concentration"]), format="%.2f")
        polymer_lot = st.text_input("Polymer Lot Number", value=existing_prep_data["Polymer Lot Number"])
        polymer_weight = st.number_input("Polymer Weight Measured (g)", value=float(existing_prep_data["Polymer Weight Measured (g)"]), format="%.2f")
        prep_date = st.date_input("Preparation Date", value=datetime.strptime(existing_prep_data["Prep Date"], "%Y-%m-%d").date())
        initials = st.text_input("Operator Initials", value=existing_prep_data["Initials"])
        notes = st.text_area("Notes", value=existing_prep_data["Notes"])
        c_sol_conc = st.number_input("C-Solution Concentration", value=float(existing_prep_data["C-Solution Concentration"]), format="%.2f")
        c_label_jar = st.text_input("C-Label for Jar", value=existing_prep_data["C-Label for jar"])
    else:
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

    submit_prep = st.form_submit_button("Submit Solution Prep Data")

if submit_prep:
    try:
        prep_sheet.append_row([
            prep_id, solution_fk, desired_conc, final_volume, solvent, solvent_lot,
            solvent_weight, polymer, polymer_start_conc, polymer_lot, polymer_weight,
            str(prep_date), initials, notes, c_sol_conc, c_label_jar
        ])
        st.success(f"✅ Solution Prep ID `{prep_id}` added successfully.")
        existing_prep_ids.append(prep_id)
    except Exception as e:
        st.error(f"❌ Error while saving Solution Prep Data: {e}")

# ------------------ COMBINED SOLUTION FORM ------------------
st.subheader("🔹 Combined Solution Entry")
with st.form("combined_solution_form"):
    combined_id = get_last_id(combined_sheet, "COMB")
    st.markdown(f"**Auto-generated Combined Solution ID:** `{combined_id}`")
    solution_id_a = st.selectbox("Select Solution ID A", existing_solution_ids, key="sol_a")
    solution_id_b = st.selectbox("Select Solution ID B", existing_solution_ids, key="sol_b")
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Combined Initials")
    combined_notes = st.text_area("Combined Notes")
    combined_label_jar = st.text_input("C-Label for Jar (Combined)")

    submit_combined = st.form_submit_button("Submit Combined Solution")

if submit_combined:
    try:
        combined_sheet.append_row([
            combined_id, solution_id_a, solution_id_b, solution_mass_a,
            solution_mass_b, str(combined_date), combined_initials,
            combined_notes, combined_label_jar
        ])
        st.success(f"✅ Combined Solution ID `{combined_id}` saved successfully.")
    except Exception as e:
        st.error(f"❌ Error while saving Combined Solution Data: {e}")


 
