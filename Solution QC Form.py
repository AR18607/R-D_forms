import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ------------- CONFIG ---------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"
QC_HEADERS = [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids", "Status"
]

# --------- Disable Enter Form Submit -----------
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# ----------- CONNECTION FUNCTIONS -------------
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

def get_last_qc_id(records):
    if not records:
        return "QC-001"
    nums = [int(r['Solution QC ID'].split('-')[-1]) for r in records if r['Solution QC ID'].startswith("QC")]
    next_num = max(nums) + 1 if nums else 1
    return f"QC-{str(next_num).zfill(3)}"

def record_status(rec):
    req_fields = ["Solution ID (FK)", "Test Date", "Dish Tare Mass (g)", "Initial Solution Mass (g)", 
                  "Final Dish Mass (g)", "Operator Initials", "QC Date", "C-Percent Solids"]
    if all(str(rec.get(f, "")).strip() not in ["", "0", "0.0"] for f in req_fields):
        return "Completed"
    return "Pending"

def disable_if_filled(value):
    return value not in [None, "", 0, 0.0]

# ----------- MAIN APP ---------------
st.title("🔬 Solution QC Form (Linked to Solution Management Form)")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
qc_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_QC, QC_HEADERS)
existing_solution_ids = get_existing_solution_ids(spreadsheet)

qc_records = qc_sheet.get_all_records()

# --------- EDIT OR NEW? -----------
pending_records = [r for r in qc_records if record_status(r) == "Pending"]
all_qc_ids = [r["Solution QC ID"] for r in qc_records]

st.markdown("#### 📝 Edit Pending (Incomplete) QC Record")
edit_id = st.selectbox("Select Pending QC ID to Edit (or leave blank for New Entry):", [""] + [r["Solution QC ID"] for r in pending_records])

if edit_id:
    # Load the record
    rec = next(r for r in qc_records if r["Solution QC ID"] == edit_id)
    edit_mode = True
else:
    rec = None
    edit_mode = False

with st.form("solution_qc_form", clear_on_submit=False):
    st.subheader("📄 Solution QC Data Entry")
    if edit_mode:
        qc_id = rec["Solution QC ID"]
        st.markdown(f"**Editing QC ID:** `{qc_id}`  _(submitted but pending)_")
    else:
        qc_id = get_last_qc_id(qc_records)
        st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")

    col1, col2 = st.columns(2)
    # Solution ID always editable (if new), else disabled
    with col1:
        solution_id_fk = st.selectbox(
            "Select Solution ID (FK)",
            existing_solution_ids,
            index=existing_solution_ids.index(rec["Solution ID (FK)"]) if rec else 0,
            disabled=edit_mode and disable_if_filled(rec.get("Solution ID (FK)"))
        ) if existing_solution_ids else st.text_input("Solution ID (FK)", value=rec["Solution ID (FK)"] if rec else "")

        test_date = st.date_input(
            "Test Date", 
            value=datetime.strptime(rec["Test Date"], "%Y-%m-%d") if rec and rec.get("Test Date") else datetime.today(),
            disabled=edit_mode and disable_if_filled(rec.get("Test Date"))
        )
        dish_tare_mass = st.number_input(
            "Dish Tare Mass (g)",
            value=float(rec["Dish Tare Mass (g)"]) if rec and rec.get("Dish Tare Mass (g)") else 0.0,
            format="%.2f",
            disabled=edit_mode and disable_if_filled(rec.get("Dish Tare Mass (g)"))
        )
        initial_solution_mass = st.number_input(
            "Initial Solution Mass (g)",
            value=float(rec["Initial Solution Mass (g)"]) if rec and rec.get("Initial Solution Mass (g)") else 0.0,
            format="%.2f",
            disabled=edit_mode and disable_if_filled(rec.get("Initial Solution Mass (g)"))
        )

    with col2:
        final_dish_mass = st.number_input(
            "Final Dish Mass (g)",
            value=float(rec["Final Dish Mass (g)"]) if rec and rec.get("Final Dish Mass (g)") else 0.0,
            format="%.2f",
            disabled=edit_mode and disable_if_filled(rec.get("Final Dish Mass (g)"))
        )
        operator_initials = st.text_input(
            "Operator Initials",
            value=rec["Operator Initials"] if rec else "",
            disabled=edit_mode and disable_if_filled(rec.get("Operator Initials"))
        )
        notes = st.text_area(
            "Notes",
            value=rec["Notes"] if rec else "",
            disabled=False
        )
        qc_date = st.date_input(
            "QC Date", 
            value=datetime.strptime(rec["QC Date"], "%Y-%m-%d") if rec and rec.get("QC Date") else datetime.today(),
            disabled=edit_mode and disable_if_filled(rec.get("QC Date"))
        )

    # Calculation before submit
    try:
        dry_polymer_weight = final_dish_mass - dish_tare_mass
        c_percent_solids = (dry_polymer_weight / initial_solution_mass) * 100 if initial_solution_mass > 0 else 0.0
    except Exception:
        c_percent_solids = 0.0

    st.markdown("**C - % solids (auto-calculated, before submit):**")
    st.code(f"{c_percent_solids:.2f} %", language="python")

    # Can only submit if at least one empty editable field is filled
    can_submit = True
    if edit_mode:
        # Prevent submit if nothing new has been filled
        can_submit = any([
            not disable_if_filled(rec.get("Test Date")) and test_date,
            not disable_if_filled(rec.get("Dish Tare Mass (g)")) and dish_tare_mass,
            not disable_if_filled(rec.get("Initial Solution Mass (g)")) and initial_solution_mass,
            not disable_if_filled(rec.get("Final Dish Mass (g)")) and final_dish_mass,
            not disable_if_filled(rec.get("Operator Initials")) and operator_initials,
            not disable_if_filled(rec.get("QC Date")) and qc_date
        ])

    submit_button = st.form_submit_button("🚀 Save QC Record", disabled=not can_submit)

# ------------- SAVE DATA -----------------
if submit_button:
    try:
        if edit_mode:
            # Find row index to update
            row_num = all_qc_ids.index(qc_id) + 2  # header + 1-based
            row_vals = [rec.get(h, "") for h in QC_HEADERS[:-2]] + [notes]  # update notes
            # Only update blank fields with new entries
            fields = [
                ("Test Date", test_date.strftime("%Y-%m-%d") if test_date else ""),
                ("Dish Tare Mass (g)", dish_tare_mass),
                ("Initial Solution Mass (g)", initial_solution_mass),
                ("Final Dish Mass (g)", final_dish_mass),
                ("Operator Initials", operator_initials),
                ("QC Date", qc_date.strftime("%Y-%m-%d") if qc_date else "")
            ]
            for (fname, val) in fields:
                if not disable_if_filled(rec.get(fname)) and val not in ["", 0, 0.0]:
                    idx = QC_HEADERS.index(fname)
                    row_vals[idx] = val

            # Recompute C-Percent Solids if relevant fields are now filled
            try:
                dry_polymer_weight = float(row_vals[5]) - float(row_vals[3])
                c_percent_solids_final = (dry_polymer_weight / float(row_vals[4])) * 100 if float(row_vals[4]) > 0 else 0.0
            except Exception:
                c_percent_solids_final = 0.0
            row_vals[9] = c_percent_solids_final

            # Set status
            status = record_status({QC_HEADERS[i]: row_vals[i] for i in range(len(QC_HEADERS)-1)})
            row_vals[10] = status
            qc_sheet.update(f"A{row_num}:K{row_num}", [row_vals])
            st.success(f"✅ QC record '{qc_id}' updated! Status: {status}")

        else:
            status = record_status({
                "Solution ID (FK)": solution_id_fk, "Test Date": test_date,
                "Dish Tare Mass (g)": dish_tare_mass, "Initial Solution Mass (g)": initial_solution_mass,
                "Final Dish Mass (g)": final_dish_mass, "Operator Initials": operator_initials,
                "QC Date": qc_date, "C-Percent Solids": c_percent_solids
            })
            qc_sheet.append_row([
                qc_id, solution_id_fk, str(test_date), dish_tare_mass,
                initial_solution_mass, final_dish_mass, operator_initials,
                notes, str(qc_date), c_percent_solids, status
            ])
            st.success(f"✅ QC record '{qc_id}' added! Status: {status}")
    except Exception as e:
        st.error(f"❌ Error saving/updating data: {e}")

# ------------- DISPLAY TABLES ---------------
st.subheader("📋 Solution QC Records Table")
df = pd.DataFrame(qc_records)
if not df.empty:
    df['Status'] = df.apply(record_status, axis=1)
    st.dataframe(df)

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
