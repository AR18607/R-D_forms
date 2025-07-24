import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"

QC_HEADERS = [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids", "Status"
]

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
    next_num = max(nums) + 1 if nums else 1
    return f"QC-{str(next_num).zfill(3)}"

def disable_if_filled(val):
    # For numbers/strings: treat None, '', 0, 0.0, '0', '0.0', '0.00', 'None' as NOT filled
    if val is None:
        return False
    try:
        if float(val) == 0.0:
            return False
    except Exception:
        if str(val).strip() in ["", "None", "0", "0.0", "0.00"]:
            return False
    return True

def is_complete_qc_record(rec):
    required_fields = [
        "Solution QC ID", "Solution ID (FK)", "Test Date",
        "Dish Tare Mass (g)", "Initial Solution Mass (g)", "Final Dish Mass (g)"
    ]
    for k in required_fields:
        val = rec.get(k, "")
        if str(val).strip() == "" or val is None or (str(val).replace(".", "", 1).isdigit() and float(val) == 0):
            return False
    return True

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

    if edit_mode:
        qc_id = selected_pending_qc["Solution QC ID"]
        solution_id_fk = selected_pending_qc["Solution ID (FK)"]
        st.info(f"Editing pending record: {qc_id} (already-filled fields are read-only, blank/zero fields are editable)")
    else:
        qc_id = get_last_qc_id(qc_sheet)
        solution_id_fk = st.selectbox("Select Solution ID (FK)", existing_solution_ids) if existing_solution_ids else st.text_input("Solution ID (FK)")

    st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")

    def fieldval(k, fallback=""):
        return selected_pending_qc.get(k, fallback) if edit_mode else fallback

    # DEBUG: print raw value for each required field
    if edit_mode:
        print("DEBUG: RAW VALUES for current record:")
        for k in ["Test Date", "Dish Tare Mass (g)", "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials", "QC Date"]:
            print(f"{k}: {repr(fieldval(k))}")

    test_date = st.date_input(
        "Test Date",
        value=pd.to_datetime(fieldval("Test Date")).date() if disable_if_filled(fieldval("Test Date")) else datetime.today().date(),
        disabled=edit_mode and disable_if_filled(fieldval("Test Date"))
    )
    dish_tare_mass = st.number_input(
        "Dish Tare Mass (g)", format="%.2f",
        value=float(fieldval("Dish Tare Mass (g)",0.0)),
        disabled=edit_mode and disable_if_filled(fieldval("Dish Tare Mass (g)"))
    )
    initial_solution_mass = st.number_input(
        "Initial Solution Mass (g)", format="%.2f",
        value=float(fieldval("Initial Solution Mass (g)",0.0)),
        disabled=edit_mode and disable_if_filled(fieldval("Initial Solution Mass (g)"))
    )
    final_dish_mass = st.number_input(
        "Final Dish Mass (g)", format="%.2f",
        value=float(fieldval("Final Dish Mass (g)",0.0)),
        disabled=edit_mode and disable_if_filled(fieldval("Final Dish Mass (g)"))
    )
    operator_initials = st.text_input(
        "Operator Initials", value=fieldval("Operator Initials"),
        disabled=edit_mode and disable_if_filled(fieldval("Operator Initials"))
    )
    notes = st.text_area("Notes", value=fieldval("Notes",""))
    qc_date = st.date_input(
        "QC Date",
        value=pd.to_datetime(fieldval("QC Date")).date() if disable_if_filled(fieldval("QC Date")) else datetime.today().date(),
        disabled=edit_mode and disable_if_filled(fieldval("QC Date"))
    )

    dry_polymer_weight = (final_dish_mass or 0) - (dish_tare_mass or 0)
    c_percent_solids = (dry_polymer_weight / (initial_solution_mass or 1)) * 100 if initial_solution_mass else 0.0

    st.markdown("**C - % solids (auto-calculated, before submit):**")
    st.code(f"{c_percent_solids:.2f} %", language="python")

    st.divider()

    # Track if any enabled field is filled/changed
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

    # Enable the submit button only if a previously blank field is now filled
    can_submit = True if not edit_mode else bool(fields_edited)
    submit_button = st.form_submit_button("💾 Save QC Record", disabled=not can_submit)

if submit_button:
    try:
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
                    "Pending" # will update below
                ]
                updated_row_dict = dict(zip(QC_HEADERS, updated_row))
                if is_complete_qc_record(updated_row_dict):
                    updated_row[-1] = "Completed"
                else:
                    updated_row[-1] = "Pending"
                    st.warning("Submitted but pending (incomplete for concentration calculation). You can revisit and fill the rest later.")
                qc_sheet.update(f"A{rownum}:K{rownum}", [updated_row])
                st.success("QC record updated successfully!")
                st.rerun()
        else:
            row = [
                qc_id, solution_id_fk, str(test_date), dish_tare_mass,
                initial_solution_mass, final_dish_mass, operator_initials,
                notes, str(qc_date), c_percent_solids, "Pending" # will update below
            ]
            row_dict = dict(zip(QC_HEADERS, row))
            if is_complete_qc_record(row_dict):
                row[-1] = "Completed"
            else:
                row[-1] = "Pending"
                st.warning("Submitted but pending (incomplete for concentration calculation). You can revisit and fill the rest later.")
            qc_sheet.append_row(row)
            st.success("QC record successfully saved!")
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving/updating data: {e}")

st.markdown("### 📝 Solution QC Records Table")
try:
    qc_records = qc_sheet.get_all_records()
    if qc_records:
        df = pd.DataFrame(qc_records)
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
