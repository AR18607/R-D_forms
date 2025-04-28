import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"
GOOGLE_CREDENTIALS_FILE = "rnd-form-sheets-b47d625d6fd9.json"

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
        # Check if first row is empty or wrong
        if worksheet.row_values(1) != headers:
            worksheet.clear()  # Optional: clear old messy stuff
            worksheet.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet


# ------------------ ID AND UTILITY FUNCTIONS ------------------

def get_existing_solution_ids(spreadsheet):
    try:
        solution_sheet = spreadsheet.worksheet("Solution ID Tbl")
        solution_ids = solution_sheet.col_values(1)[1:]  # Skip header
        return solution_ids
    except Exception as e:
        st.error(f"Error fetching Solution IDs: {e}")
        return []

def get_last_qc_id(worksheet):
    records = worksheet.col_values(1)[1:]  # Skip header
    if not records:
        return "QC-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith("QC")]
    next_num = max(nums) + 1
    return f"QC-{str(next_num).zfill(3)}"

# ------------------ MAIN APP ------------------

st.title("🔬 Solution QC Form (Linked to Solution Management Form)")

# Connect
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Solution QC tab
qc_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_QC, [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids"
])

# Fetch existing Solution IDs
existing_solution_ids = get_existing_solution_ids(spreadsheet)

with st.form("solution_qc_form"):
    st.subheader("📄 Enter Solution QC Data")

    qc_id = get_last_qc_id(qc_sheet)
    st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")

    if existing_solution_ids:
        solution_id_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids)
    else:
        solution_id_fk = st.text_input("Solution ID (FK)", placeholder="Enter manually")

    test_date = st.date_input("Test Date")
    dish_tare_mass = st.number_input("Dish Tare Mass (g)", format="%.2f")
    initial_solution_mass = st.number_input("Initial Solution Mass (g)", format="%.2f")
    final_dish_mass = st.number_input("Final Dish Mass (g)", format="%.2f")
    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    qc_date = st.date_input("QC Date")
    c_percent_solids = st.number_input("C-Percent Solids (%)", format="%.2f")

    submit_button = st.form_submit_button("🚀 Submit")

# ------------------ SAVE DATA ------------------

if submit_button:
    try:
        qc_sheet.append_row([
            qc_id, solution_id_fk, str(test_date), dish_tare_mass,
            initial_solution_mass, final_dish_mass, operator_initials,
            notes, str(qc_date), c_percent_solids
        ])
        st.success("✅ Solution QC record successfully saved!")
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")

# ------------------ DISPLAY WEEKLY QC DATA ------------------

st.subheader("📅 Solution QC Records - Last 7 Days")

try:
    qc_records = qc_sheet.get_all_records()
    if qc_records:
        df = pd.DataFrame(qc_records)
        df["QC Date"] = pd.to_datetime(df["QC Date"], errors='coerce')
        last_week_df = df[df["QC Date"] >= (datetime.now() - timedelta(days=7))]

        if not last_week_df.empty:
            st.dataframe(last_week_df)
        else:
            st.info("No QC data entered in the last 7 days.")
    else:
        st.info("No QC data found yet.")
except Exception as e:
    st.error(f"❌ Error loading weekly data: {e}")

