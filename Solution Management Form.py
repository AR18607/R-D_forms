# --- Import Required Libraries ---
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import time

# --- Configuration ---
SPREADSHEET_KEY = "1uPdUWiiwMdJCYJaxZ5TneFa9h6tbSrs327BVLT5GVPY"
SOLUTION_ID_HEADERS = ["Solution ID", "Type", "Expired", "Consumed", "C-Solution Conc"]
PREP_HEADERS = [
    "Solution Prep ID", "Solution ID (FK)", "Desired Solution Concentration", "Desired Final Volume (ml)",
    "Solvent", "Solvent Lot Number", "Solvent Weight Measured (g)", "Polymer",
    "Polymer starting concentration", "Polymer Lot Number", "Polymer Weight Measured (g)",
    "Prep Date", "Initials", "Notes", "C-Solution Concentration", "C-Label for jar"
]
COMBINED_HEADERS = [
    "Combined Solution ID", "Solution ID A", "Solution ID B",
    "Solution Mass A", "Solution Mass B", "Combined Solution Conc",
    "Date", "Initials", "Notes"
]

# --- Utility Functions ---
@st.cache_resource(ttl=600)
def connect_google_sheet(sheet_key):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_key)

def retry_open_worksheet(spreadsheet, tab_name, retries=3, wait=2):
    for i in range(retries):
        try:
            return spreadsheet.worksheet(tab_name)
        except gspread.exceptions.APIError as e:
            if i < retries - 1:
                time.sleep(wait)
            else:
                st.error(f":rotating_light: API Error while accessing tab {tab_name}: {str(e)}")
                st.stop()

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = retry_open_worksheet(spreadsheet, tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

@st.cache_data(ttl=120)
def cached_col_values(sheet_key, tab_name, col=1):
    spreadsheet = connect_google_sheet(sheet_key)
    worksheet = retry_open_worksheet(spreadsheet, tab_name)
    return worksheet.col_values(col)[1:]

@st.cache_data(ttl=120)
def cached_get_all_records(sheet_key, tab_name):
    spreadsheet = connect_google_sheet(sheet_key)
    worksheet = retry_open_worksheet(spreadsheet, tab_name)
    return worksheet.get_all_records()

def get_last_id_from_records(records, id_prefix):
    nums = [int(str(r).split('-')[-1]) for r in records if str(r).startswith(id_prefix) and str(r).split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def safe_get(record, key, default=""):
    if isinstance(record, dict):
        for k, v in record.items():
            if k.strip().lower() == key.strip().lower():
                return v
    return default

def parse_date(date_val):
    if isinstance(date_val, datetime):
        return date_val
    elif isinstance(date_val, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_val.strip(), fmt)
            except:
                continue
    return None

def get_c_solution_conc(solvent_weight, polymer_weight):
    try:
        total_weight = float(solvent_weight) + float(polymer_weight)
        return (float(polymer_weight) / total_weight) if total_weight > 0 else 0.0
    except:
        return 0.0

def get_c_from_prep(prep_rec):
    try:
        return float(prep_rec.get("C-Solution Concentration", 0.0))
    except:
        return 0.0

# --- Setup ---
spreadsheet = connect_google_sheet(SPREADSHEET_KEY)
solution_sheet = get_or_create_tab(spreadsheet, "Solution ID Tbl", SOLUTION_ID_HEADERS)
prep_sheet = get_or_create_tab(spreadsheet, "Solution Prep Data Tbl", PREP_HEADERS)
combined_sheet = get_or_create_tab(spreadsheet, "Combined Solution Tbl", COMBINED_HEADERS)

# --- Disable Enter-key submit except in TextAreas ---
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

st.markdown("# :page_facing_up: **Solution Management Form**")
st.markdown("Manage creation, preparation, and combination of solutions.")

# Load data tables
solution_records = cached_get_all_records(SPREADSHEET_KEY, "Solution ID Tbl")
prep_records = cached_get_all_records(SPREADSHEET_KEY, "Solution Prep Data Tbl")
combined_records = cached_get_all_records(SPREADSHEET_KEY, "Combined Solution Tbl")

# ========= 1. Solution ID Entry and Management =========
st.markdown("## :small_blue_diamond: Solution ID Entry / Management")

with st.expander("➕ **View/Edit Existing Solution IDs**", expanded=False):
    df = pd.DataFrame(solution_records)
    if not df.empty:
        # Show status columns and allow updating
        st.dataframe(df[["Solution ID", "Type", "Expired", "Consumed"]].style.highlight_null(null_color='orange'))
        to_edit = st.selectbox("Select Solution ID to update", options=[""] + df["Solution ID"].tolist())
        if to_edit:
            idx = df[df["Solution ID"] == to_edit].index[0]
            expired_val = st.selectbox("Expired?", ["No", "Yes"], index=0 if df.at[idx,"Expired"]=="No" else 1, key="edit_expired")
            consumed_val = st.selectbox("Consumed?", ["No", "Yes"], index=0 if df.at[idx,"Consumed"]=="No" else 1, key="edit_consumed")
            if st.button("Update Status", key="update_status_btn"):
                # Find in sheet and update
                row_number = idx+2 # header is row 1
                solution_sheet.update(f"C{row_number}:D{row_number}", [[expired_val, consumed_val]])
                st.success("Status updated. Please refresh to see the latest!")
    else:
        st.info("No Solution IDs yet.")

st.write("")

with st.form("solution_id_form", clear_on_submit=True):
    next_id = get_last_id_from_records([rec["Solution ID"] for rec in solution_records], "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{next_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['No', 'Yes'], index=0)
    consumed = st.selectbox("Consumed?", ['No', 'Yes'], index=0)
    submit_solution = st.form_submit_button("Submit New Solution ID")
if submit_solution:
    # Immediate append to Google Sheet with placeholder for C-Solution Conc
    solution_sheet.append_row([next_id, solution_type, expired, consumed, ""])
    st.success(":white_check_mark: Solution ID saved! Please refresh if not visible in the dropdown.")

# Immediately reflect latest solution IDs for next dropdowns
solution_records = cached_get_all_records(SPREADSHEET_KEY, "Solution ID Tbl")

# ========= 2. Solution Prep Form (filter IDs) =========
st.divider()
st.markdown("## :small_blue_diamond: Solution Prep Data Entry")

prep_entries = prep_records
solution_df = pd.DataFrame(solution_records)
# Only show IDs with Type = 'New' and not Expired or Consumed or Combined
prep_valid_df = solution_df[(solution_df['Type']=="New") & (solution_df['Expired']=="No") & (solution_df['Consumed']=="No")]
prep_valid_ids = prep_valid_df["Solution ID"].tolist()
selected_solution_fk = st.selectbox("Select Solution ID", options=prep_valid_ids, key="prep_solution_fk")
existing_record = next((r for r in prep_entries if r.get("Solution ID (FK)", "") == selected_solution_fk), None)
if existing_record:
    st.info(":large_yellow_circle: Existing prep entry found. Fields prefilled for update.")
else:
    st.info(":large_green_circle: No prep entry found. Enter new details.")

with st.form("prep_data_form"):
    prep_id = safe_get(existing_record, "Solution Prep ID", get_last_id_from_records(
        [r["Solution Prep ID"] for r in prep_entries if "Solution Prep ID" in r], "PREP"
    ))
    st.markdown(f"**Prep ID:** `{prep_id}`")
    desired_conc = st.number_input(
        "Desired Solution Concentration (%)",
        value=float(safe_get(existing_record, "Desired Solution Concentration", 0.0)),
        format="%.2f"
    )
    final_volume = st.number_input(
        "Desired Final Volume (ml)",
        value=float(safe_get(existing_record, "Desired Final Volume (ml)", 0.0)),
        format="%.1f"
    )
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'],
        index=['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(safe_get(existing_record, "Solvent", "IPA")) if existing_record else 0
    )
    solvent_lot = st.text_input("Solvent Lot Number", value=safe_get(existing_record, "Solvent Lot Number", ""))
    solvent_weight = st.number_input("Solvent Weight Measured (g)",
        value=float(safe_get(existing_record, "Solvent Weight Measured (g)", 0.0)),
        format="%.2f"
    )
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'],
        index=['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(safe_get(existing_record, "Polymer", "CMS-72")) if existing_record else 0
    )
    polymer_conc = st.number_input("Polymer starting concentration (%)",
        value=float(safe_get(existing_record, "Polymer starting concentration", 0.0)),
        format="%.2f"
    )
    polymer_lot = st.text_input("Polymer Lot Number", value=safe_get(existing_record, "Polymer Lot Number", ""))
    polymer_weight = st.number_input("Polymer Weight Measured (g)",
        value=float(safe_get(existing_record, "Polymer Weight Measured (g)", 0.0)),
        format="%.2f"
    )
    prep_date_str = safe_get(existing_record, "Prep Date")
    try:
        prep_date = datetime.strptime(prep_date_str, "%Y-%m-%d").date() if prep_date_str else datetime.today().date()
    except:
        prep_date = datetime.today().date()
    prep_date = st.date_input("Prep Date", value=prep_date)
    initials = st.text_input("Initials", value=safe_get(existing_record, "Initials", ""))
    notes = st.text_area("Notes", value=safe_get(existing_record, "Notes", ""))
    # Auto-calculate C-Solution Concentration
    c_sol_conc_value = get_c_solution_conc(solvent_weight, polymer_weight)
    st.markdown("**C-Solution Concentration (auto-calculated):**")
    st.code(f"{c_sol_conc_value:.4f}", language="python")
    c_label_jar = st.text_input("C-Label for jar", value=safe_get(existing_record, "C-Label for jar", ""))
    submit_prep = st.form_submit_button("Submit/Update Prep Details")
if submit_prep:
    data = [
        prep_id, selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot,
        solvent_weight, polymer, polymer_conc, polymer_lot, polymer_weight, str(prep_date),
        initials, notes, c_sol_conc_value, c_label_jar
    ]
    try:
        # Write both to prep table and update C-Solution Conc in Solution ID Tbl
        if existing_record:
            cell = prep_sheet.find(selected_solution_fk)
            row_number = cell.row
            prep_sheet.update(f"A{row_number}:P{row_number}", [data])
            # Update C-Solution Conc in solution_sheet
            sol_row = solution_df[solution_df["Solution ID"]==selected_solution_fk].index[0] + 2
            solution_sheet.update(f"E{sol_row}", [[c_sol_conc_value]])
            st.success(":white_check_mark: Prep Data updated!")
        else:
            prep_sheet.append_row(data)
            # Update C-Solution Conc in solution_sheet
            sol_row = solution_df[solution_df["Solution ID"]==selected_solution_fk].index[0] + 2
            solution_sheet.update(f"E{sol_row}", [[c_sol_conc_value]])
            st.success(":white_check_mark: Prep Data submitted!")
    except Exception as e:
        st.error(f":x: Error while writing to Google Sheet: {e}")

# ========= 3. Combined Solution Form =========
st.divider()
st.markdown("## :small_blue_diamond: Combined Solution Entry")

# IDs for Combined: exclude Expired, Consumed. Highlight Combined IDs separately
comb_valid_df = solution_df[(solution_df["Type"]=="New") & (solution_df['Expired']=="No") & (solution_df['Consumed']=="No")]
comb_valid_ids = comb_valid_df["Solution ID"].tolist()
combined_ids = solution_df[solution_df["Type"]=="Combined"]["Solution ID"].tolist()

st.markdown("**Select/Review Combined IDs:**")
st.write("IDs marked 'Combined' (already merged):")
if combined_ids:
    st.write(", ".join(combined_ids))
else:
    st.write("_No Combined Solution IDs yet._")

with st.form("combined_solution_form", clear_on_submit=True):
    combined_id = get_last_id_from_records([rec["Combined Solution ID"] for rec in combined_records], "COMB")
    st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
    # Solution A/B: Show C-Solution Conc
    solution_options = [
        f"{sid} | Conc: {safe_get(prep_rec, 'C-Solution Concentration', '?')}"
        for sid in comb_valid_ids
        for prep_rec in prep_records if prep_rec.get("Solution ID (FK)", "") == sid
    ]
    sid_to_value = {s.split(" |")[0]: float(s.split(": ")[-1]) if ": " in s else None for s in solution_options}
    solution_id_a = st.selectbox("Solution ID A", options=solution_options, key="comb_a")
    solution_id_b = st.selectbox("Solution ID B", options=solution_options, key="comb_b")
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    # Show combined concentration
    conc_a = sid_to_value.get(solution_id_a.split(" |")[0], 0)
    conc_b = sid_to_value.get(solution_id_b.split(" |")[0], 0)
    combined_mass = solution_mass_a + solution_mass_b
    combined_conc = ((solution_mass_a * conc_a) + (solution_mass_b * conc_b)) / combined_mass if combined_mass > 0 else 0.0
    st.markdown(f"**Combined Solution Concentration (auto):** `{combined_conc:.4f}`")
    st.info("🚩 Confirm with the team: Is it allowed to combine different concentrations? (Document policy!)")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Initials")
    combined_notes = st.text_area("Notes")
    submit_combined = st.form_submit_button("Submit Combined Solution Details")
if submit_combined:
    combined_sheet.append_row([
        combined_id, solution_id_a.split(" |")[0], solution_id_b.split(" |")[0],
        solution_mass_a, solution_mass_b, combined_conc,
        str(combined_date), combined_initials, combined_notes
    ])
    st.success(":white_check_mark: Combined Solution saved!")

# ========= 4. Last 7 Days Filtered Data Section =========
st.divider()
st.markdown("## 📅 Last 7 Days Data Preview (Based on Prep Date)")
today = datetime.today()
recent_prep_ids = [rec for rec in prep_records if (parsed:=parse_date(rec.get("Prep Date", ""))) and parsed >= today - timedelta(days=7)]
recent_solution_ids = set([rec.get("Solution ID (FK)", "").strip() for rec in recent_prep_ids])

st.markdown("### 📘 Solution ID Table (Filtered by Recent Prep)")
filtered_solution_ids = [rec for rec in solution_records if rec.get("Solution ID", "").strip() in recent_solution_ids]
if filtered_solution_ids:
    st.dataframe(pd.DataFrame(filtered_solution_ids))
else:
    st.write("No recent Solution ID records based on prep activity.")

st.markdown("### 🧪 Solution Prep Data (Last 7 Days Only)")
if recent_prep_ids:
    st.dataframe(pd.DataFrame(recent_prep_ids))
else:
    st.write("No Solution Prep records in the last 7 days.")

st.markdown("### 🧪 Combined Solution Data (Using Recently Prepped IDs)")
recent_combined = [rec for rec in combined_records if (cd:=parse_date(rec.get("Date", rec.get("Combined Date", "")))) and cd >= today - timedelta(days=7)]
if recent_combined:
    st.dataframe(pd.DataFrame(recent_combined))
else:
    st.write("No Combined Solution records linked to recent prep entries.")