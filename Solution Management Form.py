import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

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
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix) and r.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def fetch_recent_entries(worksheet, date_col_index, days=7):
    records = worksheet.get_all_records()
    recent_entries = []
    cutoff_date = datetime.now() - timedelta(days=days)
    for record in records:
        try:
            record_date = datetime.strptime(record[date_col_index], '%Y-%m-%d')
            if record_date >= cutoff_date:
                recent_entries.append(record)
        except:
            continue
    return recent_entries

# ------------------ MAIN APP ------------------

st.set_page_config(layout="wide")
st.title("🧪 Solution Management Form")

# Connect to Google Sheet
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Tabs
solution_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_ID, ["Solution ID", "Type", "Expired", "Consumed"])
prep_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_PREP, [
    "Solution Prep ID", "Solution ID (FK)", "Desired Solution Concentration", "Desired Final Volume",
    "Solvent", "Solvent Lot Number", "Solvent Weight Measured (g)", "Polymer", "Polymer Starting Concentration",
    "Polymer Lot Number", "Polymer Weight Measured (g)", "Prep Date", "Initials", "Notes",
    "C-Solution Concentration", "C-Label for Jar"
])
combined_sheet = get_or_create_tab(spreadsheet, TAB_COMBINED_SOLUTION, [
    "Combined Solution ID", "Solution ID A", "Solution ID B", "Solution Mass A", "Solution Mass B",
    "Date", "Initials", "Notes", "C-Label for Jar"
])

# Fetch Existing Solution IDs and Prep IDs
existing_solution_ids = solution_sheet.col_values(1)[1:]
existing_prep_ids = prep_sheet.col_values(1)[1:]

# ------------------ FORM ------------------

with st.form("solution_form"):
    st.subheader("🔹 Solution ID Entry")
    solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])

    st.subheader("🔹 Solution Prep Data Entry")
    prep_id = get_last_id(prep_sheet, "PREP")
    st.markdown(f"**Auto-generated Prep ID:** `{prep_id}`")
    solution_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids + [solution_id])
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
    solution_id_a = st.selectbox("Select Solution ID A", existing_solution_ids)
    solution_id_b = st.selectbox("Select Solution ID B", existing_solution_ids)
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Combined Initials")
    combined_notes = st.text_area("Combined Notes")
    combined_label_jar = st.text_input("C-Label for Jar (Combined)")

    # Submit Button
    submit_button = st.form_submit_button("🚀 Submit Entries")

# ------------------ SAVE DATA ------------------

if submit_button:
    try:
        # Check for duplicate Solution ID
        if solution_id in existing_solution_ids:
            st.warning(f"Solution ID `{solution_id}` already exists.")
            if not st.checkbox("Do you want to update the existing entry?"):
                st.stop()

        # Insert or update Solution ID entry
        solution_data = [solution_id, solution_type, expired, consumed]
        if solution_id in existing_solution_ids:
            cell = solution_sheet.find(solution_id)
            solution_sheet.update(f"A{cell.row}:D{cell.row}", [solution_data])
        else:
            solution_sheet.append_row(solution_data)

        # Insert Solution Prep entry
        prep_sheet.append_row([
            prep_id, solution_fk, desired_conc, final_volume, solvent, solvent_lot,
            solvent_weight, polymer, polymer_start_conc, polymer_lot, polymer_weight,
            prep_date.strftime('%Y-%m-%d'), initials, notes, c_sol_conc, c_label_jar
        ])

        # Insert Combined Solution entry
        combined_sheet.append_row([
            combined_id, solution_id_a, solution_id_b, solution_mass_a, solution_mass_b,
            combined_date.strftime('%Y-%m-%d'), combined_initials, combined_notes, combined_label_jar
        ])

        st.success("✅ Data successfully saved across all tables!")

    except Exception as e:
        st.error(f"❌ Error while saving: {e}")

# ------------------ 7-DAY REVIEW FUNCTIONALITY ------------------

st.subheader("📅 Review Entries from the Past 7 Days")

# Solution Prep Data
st.markdown("**Solution Prep Data Entries:**")
recent_prep_entries = fetch_recent_entries(prep_sheet, "Prep Date")
if recent_prep_entries:
    st.dataframe(pd.DataFrame(recent_prep_entries))
else:
    st.write("No entries found in the past 7 days.")

# Combined Solution Data
st.markdown("**Combined Solution Entries:**")
recent_combined_entries = fetch_recent_entries(combined_sheet, "Date")
if recent_combined_entries:
    st.dataframe(pd.DataFrame(recent_combined_entries))
else:
    st.write("No entries found in the past 7 days.")
