import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"

# -- Prevent accidental form submit on Enter --
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

def is_pending(row):
    required = ["Test Date", "Dish Tare Mass (g)", "Initial Solution Mass (g)",
                "Final Dish Mass (g)", "Operator Initials", "QC Date"]
    return any(not row.get(col) for col in required)

# -- MAIN --
st.title("🔬 Solution QC Form (Linked to Solution Management Form)")
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
qc_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_QC, [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids", "Status"
])
existing_solution_ids = get_existing_solution_ids(spreadsheet)
qc_records = qc_sheet.get_all_records()
qc_df = pd.DataFrame(qc_records)

if not qc_df.empty:
    qc_df["Status"] = qc_df.apply(lambda r: "pending" if is_pending(r) else "completed", axis=1)
else:
    qc_df["Status"] = ""

# ---------- VIEW/EDIT PENDING QC RECORDS -----------
st.subheader("📝 Review/Edit Pending QC Records")
pending_qc_df = qc_df[qc_df["Status"] == "pending"]
if not pending_qc_df.empty:
    st.info("The following QC records are pending completion (only these can be edited):")
    st.dataframe(pending_qc_df)
    edit_qc_id = st.selectbox("Select Pending QC ID to edit", [""] + pending_qc_df["Solution QC ID"].tolist())
    if edit_qc_id:
        record = pending_qc_df[pending_qc_df["Solution QC ID"] == edit_qc_id].iloc[0]
        with st.form("edit_pending_qc"):
            col1, col2 = st.columns(2)
            with col1:
                solution_id_fk = st.text_input("Solution ID (FK)", value=record["Solution ID (FK)"], disabled=True)
                test_date = st.date_input("Test Date", value=pd.to_datetime(record["Test Date"]).date() if record["Test Date"] else datetime.today())
                dish_tare_mass = st.number_input("Dish Tare Mass (g)", value=float(record["Dish Tare Mass (g)"] or 0), format="%.2f")
                initial_solution_mass = st.number_input("Initial Solution Mass (g)", value=float(record["Initial Solution Mass (g)"] or 0), format="%.2f")
            with col2:
                final_dish_mass = st.number_input("Final Dish Mass (g)", value=float(record["Final Dish Mass (g)"] or 0), format="%.2f")
                operator_initials = st.text_input("Operator Initials", value=record["Operator Initials"])
                notes = st.text_area("Notes", value=record["Notes"])
                qc_date = st.date_input("QC Date", value=pd.to_datetime(record["QC Date"]).date() if record["QC Date"] else datetime.today())
            # Calculation before submit
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
            submit_edit = st.form_submit_button("Update QC Record")
        if submit_edit:
            try:
                idx = qc_df[qc_df["Solution QC ID"] == edit_qc_id].index[0]
                rownum = idx + 2
                status = "pending" if any([
                    not test_date, not dish_tare_mass, not initial_solution_mass,
                    not final_dish_mass, not operator_initials, not qc_date
                ]) else "completed"
                # Prepare flat list of strings/numbers
                update_list = [
                    str(test_date), float(dish_tare_mass), float(initial_solution_mass), float(final_dish_mass),
                    operator_initials, notes, str(qc_date), float(c_percent_solids), status
                ]
                qc_sheet.update(f"C{rownum}:K{rownum}", [update_list])
                st.success("✅ QC record updated!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Error updating record: {e}")
else:
    st.info("No pending QC records found.")

st.divider()

# ----------- ADD NEW QC ENTRY ------------
st.subheader("📄 Enter Solution QC Data")
with st.form("solution_qc_form", clear_on_submit=False):
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
    submit_button = st.form_submit_button("🚀 Submit Solution QC Record")

if submit_button:
    try:
        status = "pending" if any([
            not test_date, not dish_tare_mass, not initial_solution_mass,
            not final_dish_mass, not operator_initials, not qc_date
        ]) else "completed"
        qc_sheet.append_row([
            qc_id, solution_id_fk, str(test_date), float(dish_tare_mass),
            float(initial_solution_mass), float(final_dish_mass), operator_initials,
            notes, str(qc_date), float(c_percent_solids), status
        ])
        st.success("✅ Solution QC record successfully saved!")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")

# -------- VIEW QC DATA FOR A PARTICULAR SOLUTION ---------
st.divider()
st.subheader("🔎 View All QC Records for a Solution")
selected_qc_solution = st.selectbox("Show all QC records for Solution ID", [""] + existing_solution_ids)
if selected_qc_solution:
    filtered_qc = qc_df[qc_df["Solution ID (FK)"] == selected_qc_solution]
    if not filtered_qc.empty:
        st.dataframe(filtered_qc)
    else:
        st.info("No QC records for this solution.")

# ----------- DISPLAY WEEKLY QC DATA -----------
st.divider()
st.subheader("📅 Solution QC Records - Last 7 Days")
try:
    if not qc_df.empty:
        qc_df["QC Date"] = pd.to_datetime(qc_df["QC Date"], errors='coerce')
        last_week_df = qc_df[qc_df["QC Date"] >= (datetime.now() - timedelta(days=7))]
        if not last_week_df.empty:
            st.dataframe(last_week_df)
        else:
            st.info("No QC data entered in the last 7 days.")
    else:
        st.info("No QC data found yet.")
except Exception as e:
    st.error(f"❌ Error loading weekly data: {e}")
