import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"

# ------------------ DISABLE ENTER KEY FORM SUBMIT ------------------
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

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
        if worksheet.row_values(1) != headers:
            worksheet.clear()
            worksheet.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

# ------------------ ID AND UTILITY FUNCTIONS ------------------

def get_existing_solution_ids(spreadsheet):
    try:
        solution_sheet = spreadsheet.worksheet("Solution ID Tbl")
        solution_ids = solution_sheet.col_values(1)[1:]
        return solution_ids
    except Exception as e:
        st.error(f"Error fetching Solution IDs: {e}")
        return []

def get_last_qc_id(worksheet):
    records = worksheet.col_values(1)[1:]
    if not records:
        return "QC-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith("QC")]
    next_num = max(nums) + 1
    return f"QC-{str(next_num).zfill(3)}"

# ------------------ MAIN APP ------------------

st.title("🔬 Solution QC Form (Linked to Solution Management Form)")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

qc_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_QC, [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids"
])

existing_solution_ids = get_existing_solution_ids(spreadsheet)

with st.form("solution_qc_form", clear_on_submit=False):
    st.subheader("📄 Enter Solution QC Data")

    qc_id = get_last_qc_id(qc_sheet)
    st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")

    col1, col2 = st.columns(2)

    with col1:
        solution_id_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids) if existing_solution_ids else st.text_input("Solution ID (FK)")
        test_date = st.date_input("Test Date")
        dish_tare_mass = st.number_input("Dish Tare Mass (g)", format="%.2f")
        initial_solution_mass = st.number_input("Initial Solution Mass (g)", format="%.2f")

    with col2:
        final_dish_mass = st.number_input("Final Dish Mass (g)", format="%.2f")
        operator_initials = st.text_input("Operator Initials")
        notes = st.text_area("Notes")
        qc_date = st.date_input("QC Date")

    # Auto-calculate C - % solids
    try:
        dry_polymer_weight = final_dish_mass - dish_tare_mass
        if initial_solution_mass > 0:
            c_percent_solids = (dry_polymer_weight / initial_solution_mass) * 100
        else:
            c_percent_solids = 0.0
    except:
        c_percent_solids = 0.0

    st.markdown("**C - % solids (auto-calculated):**")
    st.code(f"{c_percent_solids:.2f} %", language="python")

    st.divider()
    submit_button = st.form_submit_button("🚀 Submit Solution QC Record")

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
