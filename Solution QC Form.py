import streamlit as st 
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"
TAB_SOLUTION_ID = "Solution ID Tbl"

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

# ------------------ UTILITY FUNCTIONS ------------------
def get_existing_solution_ids(spreadsheet):
    try:
        solution_sheet = spreadsheet.worksheet(TAB_SOLUTION_ID)
        solution_ids = solution_sheet.col_values(1)[1:]
        return solution_ids
    except Exception as e:
        st.error(f"Error fetching Solution IDs: {e}")
        return []

def get_last_qc_id(worksheet):
    records = worksheet.col_values(1)[1:]
    if not records:
        return "QC-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith("QC") and r.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"QC-{str(next_num).zfill(3)}"

def get_qc_records(qc_sheet):
    records = qc_sheet.get_all_records()
    return pd.DataFrame(records)

def is_incomplete(row):
    # A row is incomplete if any of the numeric fields or initials are missing or zero
    needed_fields = [
        "Dish Tare Mass (g)", "Initial Solution Mass (g)", "Final Dish Mass (g)",
        "Operator Initials"
    ]
    for f in needed_fields:
        v = row.get(f, "")
        if v in ("", None) or (isinstance(v, (int, float)) and v == 0):
            return True
    return False

# ------------------ MAIN APP ------------------
st.title("🔬 Solution QC Form (Linked to Solution Management Form)")
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

qc_headers = [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids"
]

qc_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_QC, qc_headers)
existing_solution_ids = get_existing_solution_ids(spreadsheet)
qc_df = get_qc_records(qc_sheet) if qc_sheet else pd.DataFrame(columns=qc_headers)

# Option to filter/view all or by Solution ID
st.subheader("📑 Existing QC Entries")
solution_filter = st.selectbox("Filter by Solution ID", ["All"] + existing_solution_ids)
if solution_filter == "All":
    show_df = qc_df
else:
    show_df = qc_df[qc_df["Solution ID (FK)"] == solution_filter]

# Add pending marker for incomplete
if not show_df.empty:
    show_df = show_df.copy()
    show_df["Status"] = show_df.apply(lambda r: "pending" if is_incomplete(r) else "completed", axis=1)
    st.dataframe(show_df)
else:
    st.info("No QC entries to show.")

# If any pending, allow selection and edit
pending_records = show_df[show_df["Status"] == "pending"] if not show_df.empty else pd.DataFrame()
edit_row_idx = None
if not pending_records.empty:
    st.markdown("#### Edit Pending (Incomplete) QC Record")
    pending_options = pending_records["Solution QC ID"].tolist()
    edit_qc_id = st.selectbox("Select pending QC ID to edit", [""] + pending_options)
    if edit_qc_id:
        # Find row in full df
        edit_row_idx = qc_df[qc_df["Solution QC ID"] == edit_qc_id].index[0]
        row_data = qc_df.loc[edit_row_idx]
        # Prefill edit form
        with st.form("edit_pending_qc_form", clear_on_submit=False):
            st.markdown(f"**Editing QC ID:** `{edit_qc_id}` (status: pending)")
            col1, col2 = st.columns(2)
            with col1:
                solution_id_fk = st.text_input("Solution ID (FK)", row_data["Solution ID (FK)"], disabled=True)
                test_date = st.date_input("Test Date", pd.to_datetime(row_data["Test Date"], errors='coerce') if row_data["Test Date"] else datetime.today())
                dish_tare_mass = st.number_input("Dish Tare Mass (g)", value=float(row_data.get("Dish Tare Mass (g)", 0)), format="%.2f")
                initial_solution_mass = st.number_input("Initial Solution Mass (g)", value=float(row_data.get("Initial Solution Mass (g)", 0)), format="%.2f")
            with col2:
                final_dish_mass = st.number_input("Final Dish Mass (g)", value=float(row_data.get("Final Dish Mass (g)", 0)), format="%.2f")
                operator_initials = st.text_input("Operator Initials", row_data.get("Operator Initials", ""))
                notes = st.text_area("Notes", row_data.get("Notes", ""))
                qc_date = st.date_input("QC Date", pd.to_datetime(row_data["QC Date"], errors='coerce') if row_data["QC Date"] else datetime.today())

            # Auto-calculate C - % solids
            dry_polymer_weight = final_dish_mass - dish_tare_mass
            c_percent_solids = (dry_polymer_weight / initial_solution_mass) * 100 if initial_solution_mass > 0 else 0.0
            st.markdown("**C - % solids (auto-calculated):**")
            st.code(f"{c_percent_solids:.2f} %", language="python")

            submit_edit = st.form_submit_button("💾 Update Pending QC Record")
        if submit_edit:
            # Update in Google Sheet (by row number)
            try:
                rownum = edit_row_idx + 2  # account for header row + 0-index
                qc_sheet.update(f"C{rownum}:J{rownum}", [
                    str(test_date), dish_tare_mass, initial_solution_mass, final_dish_mass,
                    operator_initials, notes, str(qc_date), c_percent_solids
                ])
                st.success("✅ QC record updated!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Error updating record: {e}")

st.divider()
st.markdown("### ➕ **New Solution QC Record**")
with st.form("solution_qc_form", clear_on_submit=False):
    qc_id = get_last_qc_id(qc_sheet)
    st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")
    col1, col2 = st.columns(2)
    with col1:
        solution_id_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids)
        test_date = st.date_input("Test Date", value=datetime.today())
        dish_tare_mass = st.number_input("Dish Tare Mass (g)", format="%.2f")
        initial_solution_mass = st.number_input("Initial Solution Mass (g)", format="%.2f")
    with col2:
        final_dish_mass = st.number_input("Final Dish Mass (g)", format="%.2f")
        operator_initials = st.text_input("Operator Initials")
        notes = st.text_area("Notes")
        qc_date = st.date_input("QC Date", value=datetime.today())
    # Calculation preview
    dry_polymer_weight = final_dish_mass - dish_tare_mass
    c_percent_solids = (dry_polymer_weight / initial_solution_mass) * 100 if initial_solution_mass > 0 else 0.0
    st.markdown("**C - % solids (auto-calculated):**")
    st.code(f"{c_percent_solids:.2f} %", language="python")
    submit_button = st.form_submit_button("🚀 Submit Solution QC Record")

# ------------------ SAVE NEW DATA ------------------
if submit_button:
    try:
        qc_sheet.append_row([
            qc_id, solution_id_fk, str(test_date), dish_tare_mass,
            initial_solution_mass, final_dish_mass, operator_initials,
            notes, str(qc_date), c_percent_solids
        ])
        st.success("✅ Solution QC record successfully saved!")
        st.experimental_rerun()
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
