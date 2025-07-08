import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# --- CONFIG ---
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"

QC_HEADERS = [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids", "Status"
]

# --- Prevent accidental submit on Enter ---
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# --- Google Sheets Connection ---
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

# --- Helper ---
def disable_if_filled(val):
    return bool(val) and str(val).strip() not in ["", "None"]

def is_complete_qc_record(rec):
    required_fields = [
        "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
        "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
        "QC Date"
    ]
    for k in required_fields:
        if str(rec.get(k,"")).strip() == "" or rec.get(k) is None:
            return False
    return True

# --- App Start ---
st.title("🔬 Solution QC Form (Linked to Solution Management Form)")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
qc_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_QC, QC_HEADERS)

existing_solution_ids = get_existing_solution_ids(spreadsheet)
qc_records = qc_sheet.get_all_records()

# --- Select to Edit Incomplete ---
pending_qc = [r for r in qc_records if r.get("Status", "").lower() != "completed"]
pending_qc_ids = [r["Solution QC ID"] for r in pending_qc if r.get("Solution QC ID")]

edit_mode = False
selected_pending_qc = None

if pending_qc_ids:
    st.markdown("#### Edit Incomplete QC Record")
    edit_qc_id = st.selectbox("Select incomplete QC record to continue editing:", [""] + pending_qc_ids)
    if edit_qc_id:
        edit_mode = True
        selected_pending_qc = next(r for r in pending_qc if r["Solution QC ID"] == edit_qc_id)
else:
    edit_qc_id = ""

with st.form("solution_qc_form", clear_on_submit=False):
    st.subheader("📄 Enter Solution QC Data")

    # New or Edit?
    if edit_mode:
        qc_id = selected_pending_qc["Solution QC ID"]
        solution_id_fk = selected_pending_qc["Solution ID (FK)"]
        st.info(f"Editing pending record: {qc_id} (only blank fields can be updated)")
    else:
        qc_id = get_last_qc_id(qc_sheet)
        solution_id_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids) if existing_solution_ids else st.text_input("Solution ID (FK)")

    st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")

    # Get defaults, disable if already filled in record
    def fieldval(k, fallback=""):
        return selected_pending_qc.get(k, fallback) if edit_mode else fallback

    # --- Fields with disable logic ---
    test_date = st.date_input("Test Date", value=pd.to_datetime(fieldval("Test Date")).date() if disable_if_filled(fieldval("Test Date")) else datetime.today().date(), disabled=edit_mode and disable_if_filled(fieldval("Test Date")))
    dish_tare_mass = st.number_input("Dish Tare Mass (g)", format="%.2f", value=float(fieldval("Dish Tare Mass (g)",0.0)), disabled=edit_mode and disable_if_filled(fieldval("Dish Tare Mass (g)")))
    initial_solution_mass = st.number_input("Initial Solution Mass (g)", format="%.2f", value=float(fieldval("Initial Solution Mass (g)",0.0)), disabled=edit_mode and disable_if_filled(fieldval("Initial Solution Mass (g)")))
    final_dish_mass = st.number_input("Final Dish Mass (g)", format="%.2f", value=float(fieldval("Final Dish Mass (g)",0.0)), disabled=edit_mode and disable_if_filled(fieldval("Final Dish Mass (g)")))
    operator_initials = st.text_input("Operator Initials", value=fieldval("Operator Initials"), disabled=edit_mode and disable_if_filled(fieldval("Operator Initials")))
    notes = st.text_area("Notes", value=fieldval("Notes",""))
    qc_date = st.date_input("QC Date", value=pd.to_datetime(fieldval("QC Date")).date() if disable_if_filled(fieldval("QC Date")) else datetime.today().date(), disabled=edit_mode and disable_if_filled(fieldval("QC Date")))

    # --- Calculation (before submit) ---
    dry_polymer_weight = (final_dish_mass or 0) - (dish_tare_mass or 0)
    c_percent_solids = (dry_polymer_weight / (initial_solution_mass or 1)) * 100 if initial_solution_mass else 0.0

    st.markdown("**C - % solids (auto-calculated, before submit):**")
    st.code(f"{c_percent_solids:.2f} %", language="python")

    st.divider()

    # --- Detect what is being edited ---
    fields_edited = []
    if edit_mode:
        if not disable_if_filled(fieldval("Test Date")) and test_date:
            fields_edited.append("Test Date")
        if not disable_if_filled(fieldval("Dish Tare Mass (g)")) and dish_tare_mass:
            fields_edited.append("Dish Tare Mass (g)")
        if not disable_if_filled(fieldval("Initial Solution Mass (g)")) and initial_solution_mass:
            fields_edited.append("Initial Solution Mass (g)")
        if not disable_if_filled(fieldval("Final Dish Mass (g)")) and final_dish_mass:
            fields_edited.append("Final Dish Mass (g)")
        if not disable_if_filled(fieldval("Operator Initials")) and operator_initials:
            fields_edited.append("Operator Initials")
        if not disable_if_filled(fieldval("QC Date")) and qc_date:
            fields_edited.append("QC Date")

    can_submit = True if not edit_mode else bool(fields_edited)
    submit_button = st.form_submit_button("💾 Save QC Record", disabled=not can_submit)

# --- Save Logic ---
if submit_button:
    try:
        # Build row or update
        status = "Completed"
        # For completion, all required fields must be filled!
        if edit_mode:
            rownum = None
            for i, rec in enumerate(qc_records):
                if rec.get("Solution QC ID") == qc_id:
                    rownum = i+2 # header is 1
                    break
            if not rownum:
                st.error("Record not found for update!")
            else:
                updated_row = [
                    qc_id,
                    solution_id_fk,
                    str(test_date) if not disable_if_filled(fieldval("Test Date")) else fieldval("Test Date"),
                    dish_tare_mass if not disable_if_filled(fieldval("Dish Tare Mass (g)")) else fieldval("Dish Tare Mass (g)"),
                    initial_solution_mass if not disable_if_filled(fieldval("Initial Solution Mass (g)")) else fieldval("Initial Solution Mass (g)"),
                    final_dish_mass if not disable_if_filled(fieldval("Final Dish Mass (g)")) else fieldval("Final Dish Mass (g)"),
                    operator_initials if not disable_if_filled(fieldval("Operator Initials")) else fieldval("Operator Initials"),
                    notes,
                    str(qc_date) if not disable_if_filled(fieldval("QC Date")) else fieldval("QC Date"),
                    c_percent_solids if not disable_if_filled(fieldval("C-Percent Solids")) else fieldval("C-Percent Solids"),
                    status
                ]
                # Mark as pending if any required field is missing
                req = updated_row[:9]
                if "" in [str(x).strip() for x in req] or "None" in [str(x).strip() for x in req]:
                    status = "Pending"
                    updated_row[-1] = status
                    st.warning("Submitted but pending (incomplete). You can revisit and fill the rest later.")

                qc_sheet.delete_row(rownum)
                qc_sheet.insert_row(updated_row, rownum)
                st.success("QC record updated successfully!")
                st.rerun()
        else:
            # New record: allow partial fill
            row = [
                qc_id, solution_id_fk, str(test_date), dish_tare_mass,
                initial_solution_mass, final_dish_mass, operator_initials,
                notes, str(qc_date), c_percent_solids, status
            ]
            req = row[:9]
            if "" in [str(x).strip() for x in req] or "None" in [str(x).strip() for x in req]:
                status = "Pending"
                row[-1] = status
                st.warning("Submitted but pending (incomplete). You can revisit and fill the rest later.")
            qc_sheet.append_row(row)
            st.success("QC record successfully saved!")
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving/updating data: {e}")

# --- Show All Data as Table, Mark Pending ---
st.markdown("### 📝 Solution QC Records Table")

try:
    qc_records = qc_sheet.get_all_records()
    if qc_records:
        df = pd.DataFrame(qc_records)
        # Mark pending visually
        def pending_note(row):
            if row.get("Status","").lower() == "pending":
                return "⏳ PENDING - revisit to complete"
            elif is_complete_qc_record(row):
                return "✔️ Completed"
            return ""
        df["Record Status"] = df.apply(pending_note, axis=1)
        st.dataframe(df)
    else:
        st.info("No QC data found yet.")
except Exception as e:
    st.error(f"❌ Error loading QC data: {e}")

# ----------- Recent 7 Day Table -------------
st.subheader("📅 Solution QC Records - Last 7 Days")
if not df.empty:
    df["QC Date"] = pd.to_datetime(df["QC Date"], errors='coerce')
    last_week_df = df[df["QC Date"] >= (datetime.now() - timedelta(days=7))]
    if not last_week_df.empty:
        st.dataframe(last_week_df)
    else:
        st.info("No QC data entered in the last 7 days.")
else:
    st.info("No QC data found yet.")
