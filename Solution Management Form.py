
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
    records = worksheet.col_values(1)[1:]  # Skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def get_recent_entries(worksheet, date_col_index):
    records = worksheet.get_all_records()
    seven_days_ago = datetime.today() - timedelta(days=7)
    filtered = [r for r in records if datetime.strptime(r[date_col_index], '%Y-%m-%d') >= seven_days_ago]
    return filtered

# ------------------ STREAMLIT FORM ------------------

st.title("🧪 Solution Management Form (3 Tabs, Dynamic IDs)")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

solution_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_ID, ["Solution ID", "Type", "Expired", "Consumed"])
prep_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_PREP, [
    "Solution Prep ID", "Solution ID (FK)", "Desired Concentration", "Final Volume",
    "Solvent", "Solvent Lot", "Solvent Weight", "Polymer", "Polymer Concentration",
    "Polymer Lot", "Polymer Weight", "Prep Date", "Initials", "Notes"
])
combined_sheet = get_or_create_tab(spreadsheet, TAB_COMBINED_SOLUTION, [
    "Combined Solution ID", "Solution ID A", "Solution ID B", "Solution Mass A",
    "Solution Mass B", "Date", "Initials", "Notes"
])

existing_solution_ids = solution_sheet.col_values(1)[1:]
existing_prep_ids = prep_sheet.col_values(1)[1:]

with st.form("solution_id_form"):
    st.subheader("🔹 Solution ID Entry")
    solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])
    submit_solution = st.form_submit_button("Submit Solution ID")

with st.form("prep_data_form"):
    st.subheader("🔹 Solution Prep Data Entry")
    prep_id = get_last_id(prep_sheet, "PREP")
    st.markdown(f"**Auto-generated Prep ID:** `{prep_id}`")
    solution_fk = st.selectbox("Select Solution ID", existing_solution_ids)

    if solution_fk in existing_solution_ids:
        st.warning("This Solution ID already exists. Do you want to modify its entry?")

    desired_conc = st.number_input("Desired Concentration (%)", format="%.2f")
    final_volume = st.number_input("Final Volume", format="%.1f")
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'])
    solvent_lot = st.text_input("Solvent Lot Number")
    solvent_weight = st.number_input("Solvent Weight (g)", format="%.2f")
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'])
    polymer_conc = st.number_input("Polymer Concentration (%)", format="%.2f")
    polymer_lot = st.text_input("Polymer Lot Number")
    polymer_weight = st.number_input("Polymer Weight (g)", format="%.2f")
    prep_date = st.date_input("Preparation Date")
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    submit_prep = st.form_submit_button("Submit Prep Data")

with st.form("combined_solution_form"):
    st.subheader("🔹 Combined Solution Entry")
    combined_id = get_last_id(combined_sheet, "COMB")
    st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
    solution_id_a = st.selectbox("Solution ID A", existing_solution_ids)
    solution_id_b = st.selectbox("Solution ID B", existing_solution_ids)
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Initials")
    combined_notes = st.text_area("Notes")
    submit_combined = st.form_submit_button("Submit Combined Solution")

if submit_solution:
    solution_sheet.append_row([solution_id, solution_type, expired, consumed])
    st.success("✅ Solution ID saved!")

if submit_prep:
    prep_sheet.append_row([prep_id, solution_fk, desired_conc, final_volume, solvent, solvent_lot,
        solvent_weight, polymer, polymer_conc, polymer_lot, polymer_weight,
        str(prep_date), initials, notes])
    st.success("✅ Prep Data saved!")

if submit_combined:
    combined_sheet.append_row([combined_id, solution_id_a, solution_id_b, solution_mass_a,
        solution_mass_b, str(combined_date), combined_initials, combined_notes])
    st.success("✅ Combined Solution saved!")

# Review last 7 days' entries
st.subheader("🔹 Review Recent Entries")
if st.button("View Last 7 Days Entries"):
    recent_prep_entries = get_recent_entries(prep_sheet, "Prep Date")
    recent_combined_entries = get_recent_entries(combined_sheet, "Date")

    st.write("**Recent Prep Entries:**", recent_prep_entries)
    st.write("**Recent Combined Entries:**", recent_combined_entries)

