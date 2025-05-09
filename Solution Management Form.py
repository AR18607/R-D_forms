import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
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
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDENTIALS), scope)
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

def fetch_row_by_value(worksheet, column_index, value):
    records = worksheet.get_all_records()
    for record in records:
        if record[list(record.keys())[column_index - 1]] == value:
            return record
    return None

# ------------------ STREAMLIT FORM ------------------

st.title("🧪 Solution Management Form")

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
    "Combined Solution ID", "Solution ID A", "Solution ID B", "Solution Mass A",
    "Solution Mass B", "Date", "Initials", "Notes", "C-Label for jar"
])

# Fetch Existing Solution IDs and Prep IDs
existing_solution_ids = solution_sheet.col_values(1)[1:]
existing_prep_ids = prep_sheet.col_values(1)[1:]

# ------------------ Solution ID Entry ------------------
st.subheader("🔹 Solution ID Entry")
with st.form("solution_id_form"):
    solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{solution_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['Yes', 'No'])
    consumed = st.selectbox("Consumed?", ['Yes', 'No'])
    submit_solution_id = st.form_submit_button("Submit Solution ID")

if submit_solution_id:
    try:
        solution_sheet.append_row([solution_id, solution_type, expired, consumed])
        st.success(f"✅ Solution ID `{solution_id}` saved successfully!")
        existing_solution_ids.append(solution_id)  # Update the list with the new ID
    except Exception as e:
        st.error(f"❌ Error while saving Solution ID: {e}")

# ------------------ Solution Prep Data Entry ------------------
st.subheader("🔹 Solution Prep Data Entry")
with st.form("solution_prep_form"):
    prep_id = get_last_id(prep_sheet, "PREP")
    st.markdown(f"**Auto-generated Prep ID:** `{prep_id}`")
    solution_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids)

    # Check if the selected Solution ID has existing prep data
    existing_prep_data = fetch_row_by_value(prep_sheet, 2, solution_fk)

    desired_conc = st.number_input("Desired Solution Concentration (%)", format="%.2f",
                                   value=float(existing_prep_data["Desired Solution Concentration"]) if existing_prep_data else 0.0)
    final_volume = st.number_input("Desired Final Volume", format="%.1f",
                                   value=float(existing_prep_data["Desired Final Volume"]) if existing_prep_data else 0.0)
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'],
                           index=['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(existing_prep_data["Solvent"]) if existing_prep_data else 0)
    solvent_lot = st.text_input("Solvent Lot Number",
                                value=existing_prep_data["Solvent Lot Number"] if existing_prep_data else "")
    solvent_weight = st.number_input("Solvent Weight Measured (g)", format="%.2f",
                                     value=float(existing_prep_data["Solvent Weight Measured (g)"]) if existing_prep_data else 0.0)
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'],
                           index=['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(existing_prep_data["Polymer"]) if existing_prep_data else 0)
    polymer_start_conc = st.number_input("Polymer Starting Concentration (%)", format="%.2f",
                                         value=float(existing_prep_data["Polymer starting concentration"]) if existing_prep_data else 0.0)
    polymer_lot = st.text_input("Polymer Lot Number",
                                value=existing_prep_data["Polymer Lot Number"] if existing_prep_data else "")
    polymer_weight = st.number_input("Polymer Weight Measured (g)", format="%.2f",
                                     value=float(existing_prep_data["Polymer Weight Measured (g)"]) if existing_prep_data else 0.0)
    prep_date = st.date_input("Preparation Date",
                              value=datetime.strptime(existing_prep_data["Prep Date"], "%Y-%m-%d") if existing_prep_data else datetime.today())
    initials = st.text_input("Operator Initials",
                             value=existing_prep_data["Initials"] if existing_prep_data else "")
    notes = st.text_area("Notes",
                         value=existing_prep_data["Notes"] if existing_prep_data else "")
    c_sol_conc = st.number_input("C-Solution Concentration", format="%.2f",
                                 value=float(existing_prep_data["C-Solution Concentration"]) if existing_prep_data else 0.0)
    c_label_jar = st.text_input("C-Label for Jar",
                                value=existing_prep_data["C-Label for jar"] if existing_prep_data else "")
    submit_prep = st.form_submit_button("Submit Solution Prep Data")

if submit_prep:
    try:
        prep_sheet.append_row([
            prep_id, solution_fk, desired_conc, final_volume, solvent, solvent_lot,
            solvent_weight, polymer, polymer_start_conc, polymer_lot, polymer_weight,
            str(prep_date), initials, notes, c_sol_conc, c_label_jar
        ])
        st.success(f"✅ Solution Prep Data for `{solution_fk}` saved successfully!")
        existing_prep_ids.append(prep_id)  # Update the list with the new Prep ID
    except Exception as e:
        st.error(f"❌ Error while saving Solution Prep Data: {e}")

# ------------------ Combined Solution Entry ------------------
st.subheader("🔹 Combined Solution Entry")
with st.form("combined_solution_form"):
    combined_id = get_last_id(combined_sheet, "COMB")
    st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
    solution_id_a = st.selectbox("Select Solution ID A", existing_solution_ids, key="sol_a")
    solution_id_b = st.selectbox("Select Solution ID B", existing_solution_ids, key="sol_b")
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Combined Initials")
    combined_notes = st.text_area("Combined Notes")
    combined_label_jar = st.text_input("C-Label for Jar (Combined)")
    submit_combined = st.form_submit_button("Submit Combined Solution Data")

if submit_combined:
    try:
        combined_sheet.append_row([
            combined_id, solution_id_a, solution_id_b, solution_mass_a,
            solution_mass_b, str(combined_date), combined_initials, combined_notes, combined_label_jar
        ])
        st.success(f"✅ Combined Solution `{combined_id}` saved successfully!")
    except Exception as e:
        st.error(f"❌ Error while saving Combined Solution Data: {e}")


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
