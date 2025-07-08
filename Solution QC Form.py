import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ------------- CONFIG -------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_QC = "Solution QC Tbl"
TAB_SOLUTION_ID = "Solution ID Tbl"
QC_HEADERS = [
    "Solution QC ID", "Solution ID (FK)", "Test Date", "Dish Tare Mass (g)",
    "Initial Solution Mass (g)", "Final Dish Mass (g)", "Operator Initials",
    "Notes", "QC Date", "C-Percent Solids", "Status"
]

# ------------- Disable ENTER key submit -------------
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# ------------- CONNECTIONS -------------

@st.cache_resource(ttl=600)
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

def get_solution_ids(spreadsheet):
    try:
        sol_sheet = spreadsheet.worksheet(TAB_SOLUTION_ID)
        solution_ids = sol_sheet.col_values(1)[1:]
        return solution_ids
    except Exception:
        return []

def get_next_qc_id(records):
    if not records:
        return "QC-001"
    nums = [int(r["Solution QC ID"].split('-')[-1]) for r in records if r["Solution QC ID"].startswith("QC")]
    next_num = max(nums) + 1 if nums else 1
    return f"QC-{str(next_num).zfill(3)}"

def record_status(rec):
    # "incomplete" if any of the main fields (except ID, FK, Notes) is blank
    fields = ["Test Date", "Dish Tare Mass (g)", "Initial Solution Mass (g)",
              "Final Dish Mass (g)", "Operator Initials", "QC Date"]
    return "incomplete" if any(str(rec.get(f, "")).strip() == "" for f in fields) else "complete"

# ------------- MAIN APP -------------

st.title("🔬 Solution QC Form (Linked to Solution Management Form)")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
qc_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_QC, QC_HEADERS)

# Always work with latest data
qc_records = qc_sheet.get_all_records()
solution_ids = get_solution_ids(spreadsheet)

# Update Status for all records
for i, rec in enumerate(qc_records):
    status = record_status(rec)
    if rec.get("Status", "") != status:
        # update sheet if status changed
        qc_sheet.update(f"K{i+2}", status)
        rec["Status"] = status

# Separate incomplete & completed records
incomplete_qc = [r for r in qc_records if r["Status"] == "incomplete"]
completed_qc = [r for r in qc_records if r["Status"] == "complete"]

# ---- Main page: Choose "New QC Entry" or "Edit Incomplete QC" ----
mode = st.radio("Choose Action", ["New QC Entry", "Edit Pending QC Entry"], horizontal=True)

# ---- EDIT INCOMPLETE QC ENTRY ----
if mode == "Edit Pending QC Entry":
    if incomplete_qc:
        sel_id = st.selectbox("Select Pending QC Record", [r["Solution QC ID"] for r in incomplete_qc])
        rec = next(r for r in incomplete_qc if r["Solution QC ID"] == sel_id)

        with st.form("edit_qc_form", clear_on_submit=False):
            st.markdown(f"**Editing QC Record:** `{sel_id}` (Only empty fields are editable)")
            st.info("This entry was submitted but is still pending (incomplete fields remain).")
            # Disable fields with values
            def field_input(label, key, dtype="text"):
                val = rec.get(key, "")
                disabled = str(val).strip() != ""
                if dtype == "number":
                    v = float(val) if str(val).strip() != "" else 0.0
                    return st.number_input(label, value=v, disabled=disabled, format="%.2f")
                elif dtype == "date":
                    try:
                        v = pd.to_datetime(val) if str(val).strip() else datetime.now()
                    except:
                        v = datetime.now()
                    return st.date_input(label, value=v, disabled=disabled)
                else:
                    return st.text_input(label, value=val, disabled=disabled)

            solution_id_fk = st.text_input("Solution ID (FK)", value=rec.get("Solution ID (FK)"), disabled=True)
            test_date = field_input("Test Date", "Test Date", dtype="date")
            dish_tare_mass = field_input("Dish Tare Mass (g)", "Dish Tare Mass (g)", dtype="number")
            initial_solution_mass = field_input("Initial Solution Mass (g)", "Initial Solution Mass (g)", dtype="number")
            final_dish_mass = field_input("Final Dish Mass (g)", "Final Dish Mass (g)", dtype="number")
            operator_initials = field_input("Operator Initials", "Operator Initials", dtype="text")
            notes = st.text_area("Notes", value=rec.get("Notes", ""), disabled=False)
            qc_date = field_input("QC Date", "QC Date", dtype="date")

            # Calculation (if all inputs present)
            try:
                dry_polymer_weight = float(final_dish_mass) - float(dish_tare_mass)
                c_percent_solids = (dry_polymer_weight / float(initial_solution_mass)) * 100 if float(initial_solution_mass) > 0 else 0.0
            except:
                c_percent_solids = 0.0
            st.markdown(f"**C - % solids (auto-calculated):** `{c_percent_solids:.2f} %`")

            update_btn = st.form_submit_button("Update Pending QC Record")
            if update_btn:
                # Only update missing fields!
                update_vals = [
                    rec["Solution QC ID"],
                    rec["Solution ID (FK)"],
                    str(test_date) if not rec.get("Test Date") else rec["Test Date"],
                    dish_tare_mass if str(rec.get("Dish Tare Mass (g)", "")).strip() == "" else rec["Dish Tare Mass (g)"],
                    initial_solution_mass if str(rec.get("Initial Solution Mass (g)", "")).strip() == "" else rec["Initial Solution Mass (g)"],
                    final_dish_mass if str(rec.get("Final Dish Mass (g)", "")).strip() == "" else rec["Final Dish Mass (g)"],
                    operator_initials if str(rec.get("Operator Initials", "")).strip() == "" else rec["Operator Initials"],
                    notes,
                    str(qc_date) if not rec.get("QC Date") else rec["QC Date"],
                    c_percent_solids,
                    "",  # Placeholder for status, will update below
                ]
                # Determine status
                update_status = "incomplete"
                required = update_vals[2:9]
                if all(str(x).strip() not in ["", "0", "0.0"] for x in required):
                    update_status = "complete"
                update_vals[-1] = update_status

                # Find row number in sheet (2-based, since 1 is header)
                row_num = next(i+2 for i, r in enumerate(qc_records) if r["Solution QC ID"] == sel_id)
                qc_sheet.update(f"A{row_num}:K{row_num}", [update_vals])
                st.success("Record updated.")
                st.experimental_rerun()
    else:
        st.info("No pending/incomplete QC entries to edit.")

# ---- NEW QC ENTRY ----
if mode == "New QC Entry":
    with st.form("new_qc_form", clear_on_submit=True):
        st.subheader("📄 Enter Solution QC Data")
        qc_id = get_next_qc_id(qc_records)
        st.markdown(f"**Auto-generated QC ID:** `{qc_id}`")
        solution_id_fk = st.selectbox("Select Solution ID (FK)", solution_ids)
        test_date = st.date_input("Test Date")
        dish_tare_mass = st.number_input("Dish Tare Mass (g)", format="%.2f")
        initial_solution_mass = st.number_input("Initial Solution Mass (g)", format="%.2f")
        final_dish_mass = st.number_input("Final Dish Mass (g)", format="%.2f")
        operator_initials = st.text_input("Operator Initials")
        notes = st.text_area("Notes")
        qc_date = st.date_input("QC Date")

        try:
            dry_polymer_weight = final_dish_mass - dish_tare_mass
            c_percent_solids = (dry_polymer_weight / initial_solution_mass) * 100 if initial_solution_mass > 0 else 0.0
        except:
            c_percent_solids = 0.0
        st.markdown(f"**C - % solids (auto-calculated):** `{c_percent_solids:.2f} %`")

        submit_btn = st.form_submit_button("🚀 Submit QC Record")
        if submit_btn:
            status = record_status({
                "Test Date": test_date,
                "Dish Tare Mass (g)": dish_tare_mass,
                "Initial Solution Mass (g)": initial_solution_mass,
                "Final Dish Mass (g)": final_dish_mass,
                "Operator Initials": operator_initials,
                "QC Date": qc_date
            })
            try:
                qc_sheet.append_row([
                    qc_id, solution_id_fk, str(test_date), dish_tare_mass,
                    initial_solution_mass, final_dish_mass, operator_initials,
                    notes, str(qc_date), c_percent_solids, status
                ])
                if status == "incomplete":
                    st.warning("Record submitted but is pending (incomplete fields remain).")
                else:
                    st.success("✅ QC record successfully saved!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Error saving data: {e}")

# ---- Display as Table for each Solution ----
st.markdown("---")
st.subheader("📊 All QC Data for Each Solution")
if qc_records:
    df_qc = pd.DataFrame(qc_records)
    solution_id_to_show = st.selectbox("Show QC table for Solution ID", sorted(set(df_qc["Solution ID (FK)"])))
    st.dataframe(df_qc[df_qc["Solution ID (FK)"] == solution_id_to_show])
else:
    st.info("No QC records found yet.")

# ---- Last 7 Days ----
st.markdown("---")
st.subheader("📅 Solution QC Records - Last 7 Days")
try:
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
