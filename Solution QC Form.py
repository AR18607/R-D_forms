import streamlit as st 
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"
TAB_SOLUTION_ID = "Solution ID Tbl"

st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

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

def get_existing_solution_ids(spreadsheet):
    try:
        solution_sheet = spreadsheet.worksheet(TAB_SOLUTION_ID)
        return solution_sheet.col_values(1)[1:]
    except Exception as e:
        st.error(f"Error fetching Solution IDs: {e}")
        return []

def get_last_qc_id(worksheet):
    records = worksheet.col_values(1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith("QC") and r.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"QC-{str(next_num).zfill(3)}"

def get_qc_records(qc_sheet):
    records = qc_sheet.get_all_records()
    return pd.DataFrame(records)

def is_incomplete(row):
    # Mark as pending if any essential fields are missing or zero
    essentials = ["Dish Tare Mass (g)", "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials"]
    for f in essentials:
        v = row.get(f, "")
        if v in ("", None) or (isinstance(v, (int, float)) and v == 0):
            return True
    return False

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

# 1. Select Solution ID to view ALL records for it
st.subheader("📑 QC Data Table for Selected Solution ID")
selected_sol = st.selectbox("Select Solution ID", existing_solution_ids)
df_sol = qc_df[qc_df["Solution ID (FK)"] == selected_sol] if not qc_df.empty else pd.DataFrame()
if not df_sol.empty:
    df_sol = df_sol.copy()
    df_sol["Status"] = df_sol.apply(lambda r: "submitted but pending" if is_incomplete(r) else "completed", axis=1)
    st.dataframe(df_sol)
else:
    st.info("No QC records for this Solution ID.")

# 2. Only allow editing incomplete records
pending_df = df_sol[df_sol["Status"] == "submitted but pending"] if not df_sol.empty else pd.DataFrame()
if not pending_df.empty:
    st.markdown("#### Edit Pending (Incomplete) QC Record")
    edit_qc_id = st.selectbox("Select pending QC ID to edit", [""] + pending_df["Solution QC ID"].tolist())
    if edit_qc_id:
        edit_row = pending_df[pending_df["Solution QC ID"] == edit_qc_id].iloc[0]
        with st.form("edit_pending_qc_form", clear_on_submit=False):
            st.markdown(f"**Editing QC ID:** `{edit_qc_id}` (status: pending)")
            col1, col2 = st.columns(2)
            with col1:
                dish_tare_mass = st.number_input("Dish Tare Mass (g)", value=float(edit_row["Dish Tare Mass (g)"] or 0), format="%.2f")
                initial_solution_mass = st.number_input("Initial Solution Mass (g)", value=float(edit_row["Initial Solution Mass (g)"] or 0), format="%.2f")
                test_date = st.date_input("Test Date", pd.to_datetime(edit_row["Test Date"], errors='coerce') if edit_row["Test Date"] else datetime.today())
            with col2:
                final_dish_mass = st.number_input("Final Dish Mass (g)", value=float(edit_row["Final Dish Mass (g)"] or 0), format="%.2f")
                operator_initials = st.text_input("Operator Initials", value=edit_row["Operator Initials"])
                notes = st.text_area("Notes", value=edit_row["Notes"])
                qc_date = st.date_input("QC Date", pd.to_datetime(edit_row["QC Date"], errors='coerce') if edit_row["QC Date"] else datetime.today())

            dry_polymer_weight = final_dish_mass - dish_tare_mass
            c_percent_solids = (dry_polymer_weight / initial_solution_mass) * 100 if initial_solution_mass > 0 else 0.0
            st.markdown("**C - % solids (auto-calculated):**")
            st.code(f"{c_percent_solids:.2f} %", language="python")
            submit_edit = st.form_submit_button("💾 Update Pending QC Record")
        if submit_edit:
            try:
                idx = qc_df[qc_df["Solution QC ID"] == edit_qc_id].index[0]
                rownum = idx + 2
                qc_sheet.update(f"C{rownum}:J{rownum}", [
                    str(test_date), dish_tare_mass, initial_solution_mass, final_dish_mass,
                    operator_initials, notes, str(qc_date), c_percent_solids
                ])
                st.success("✅ QC record updated!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Error updating record: {e}")
else:
    st.info("No pending QC entries for this Solution ID. You may add a new record below.")

st.divider()
# 3. Only allow new entry if no pending
if pending_df.empty:
    st.markdown("### ➕ New Solution QC Record")
    with st.form("solution_qc_form", clear_on_submit=False):
        qc_id = get_last_qc_id(qc_sheet)
        st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")
        col1, col2 = st.columns(2)
        with col1:
            test_date = st.date_input("Test Date", value=datetime.today())
            dish_tare_mass = st.number_input("Dish Tare Mass (g)", format="%.2f")
            initial_solution_mass = st.number_input("Initial Solution Mass (g)", format="%.2f")
        with col2:
            final_dish_mass = st.number_input("Final Dish Mass (g)", format="%.2f")
            operator_initials = st.text_input("Operator Initials")
            notes = st.text_area("Notes")
            qc_date = st.date_input("QC Date", value=datetime.today())
        dry_polymer_weight = final_dish_mass - dish_tare_mass
        c_percent_solids = (dry_polymer_weight / initial_solution_mass) * 100 if initial_solution_mass > 0 else 0.0
        st.markdown("**C - % solids (auto-calculated):**")
        st.code(f"{c_percent_solids:.2f} %", language="python")
        submit_button = st.form_submit_button("🚀 Submit Solution QC Record")
    if submit_button:
        try:
            qc_sheet.append_row([
                qc_id, selected_sol, str(test_date), dish_tare_mass,
                initial_solution_mass, final_dish_mass, operator_initials,
                notes, str(qc_date), c_percent_solids
            ])
            st.success("✅ Solution QC record successfully saved!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"❌ Error saving data: {e}")

# 4. Last 7 days view for all data
st.subheader("📅 Solution QC Records - Last 7 Days")
try:
    df = qc_df.copy()
    df["QC Date"] = pd.to_datetime(df["QC Date"], errors='coerce')
    last_week_df = df[df["QC Date"] >= (datetime.now() - timedelta(days=7))]
    if not last_week_df.empty:
        st.dataframe(last_week_df)
    else:
        st.info("No QC data entered in the last 7 days.")
except Exception as e:
    st.error(f"❌ Error loading weekly data: {e}")
