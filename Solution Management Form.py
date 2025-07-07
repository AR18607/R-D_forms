import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import time

# --- Google Sheets Config ---
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

# --- Prevent accidental form submit on Enter ---
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

st.markdown("# 📄 Solution Management Form")
st.markdown("Manage creation, preparation, and combination of solutions.")

spreadsheet = connect_google_sheet(SPREADSHEET_KEY)
solution_sheet = get_or_create_tab(spreadsheet, "Solution ID Tbl", SOLUTION_ID_HEADERS)
prep_sheet = get_or_create_tab(spreadsheet, "Solution Prep Data Tbl", PREP_HEADERS)
combined_sheet = get_or_create_tab(spreadsheet, "Combined Solution Tbl", COMBINED_HEADERS)

# -- Always load records FRESH, at this point --
solution_records = cached_get_all_records(SPREADSHEET_KEY, "Solution ID Tbl")
prep_records = cached_get_all_records(SPREADSHEET_KEY, "Solution Prep Data Tbl")
combined_records = cached_get_all_records(SPREADSHEET_KEY, "Combined Solution Tbl")

def label_status(row):
    label = row["Solution ID"]
    if row.get("Expired", "No") == "Yes":
        label += " (expired)"
    elif row.get("Consumed", "No") == "Yes":
        label += " (consumed)"
    elif row.get("Type", "New") == "Combined":
        label += " (combined)"
    return label

# ------------------- Solution ID Management -------------------
st.markdown("## 🔹 Solution ID Entry / Management")
with st.expander("View / Update Existing Solution IDs", expanded=False):
    df = pd.DataFrame(solution_records)
    if not df.empty:
        df["Label"] = df.apply(label_status, axis=1)
        st.dataframe(df[["Solution ID", "Type", "Expired", "Consumed"]])
        to_edit = st.selectbox("Select Solution ID to update", options=[""] + df["Solution ID"].tolist())
        if to_edit:
            idx = df[df["Solution ID"] == to_edit].index[0]
            expired_val = st.selectbox("Expired?", ["No", "Yes"], index=0 if df.at[idx,"Expired"]=="No" else 1, key="edit_expired")
            consumed_val = st.selectbox("Consumed?", ["No", "Yes"], index=0 if df.at[idx,"Consumed"]=="No" else 1, key="edit_consumed")
            if st.button("Update Status", key="update_status_btn"):
                row_number = idx+2
                solution_sheet.update(f"C{row_number}:D{row_number}", [[expired_val, consumed_val]])
                st.cache_data.clear()
                st.success("Status updated!")
                st.experimental_rerun()
    else:
        st.info("No Solution IDs yet.")

with st.form("solution_id_form", clear_on_submit=True):
    next_id = get_last_id_from_records([rec["Solution ID"] for rec in solution_records], "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{next_id}` _(will only be saved on submit)_")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['No', 'Yes'], index=0)
    consumed = st.selectbox("Consumed?", ['No', 'Yes'], index=0)
    submit_solution = st.form_submit_button("Submit New Solution ID")
if submit_solution:
    solution_sheet.append_row([next_id, solution_type, expired, consumed, ""])
    st.cache_data.clear()
    st.success(":white_check_mark: Solution ID saved! Dropdowns and tables updated.")
    st.experimental_rerun()

# Reload records after possible rerun
solution_records = cached_get_all_records(SPREADSHEET_KEY, "Solution ID Tbl")
df_solution = pd.DataFrame(solution_records)
df_solution["Label"] = df_solution.apply(label_status, axis=1)
prep_records = cached_get_all_records(SPREADSHEET_KEY, "Solution Prep Data Tbl")
combined_records = cached_get_all_records(SPREADSHEET_KEY, "Combined Solution Tbl")

# ------------------- Solution Prep Data Entry -------------------
st.markdown("---")
st.markdown("## 🔹 Solution Prep Data Entry")

prep_valid_df = df_solution[
    ((df_solution['Type'].isin(["New", "Combined"])) &
     ~((df_solution['Expired'] == "Yes") & (df_solution['Consumed'] == "Yes")))
]
prep_valid_ids = prep_valid_df["Solution ID"].tolist()
selected_solution_fk = st.selectbox("Select Solution ID", options=prep_valid_ids, key="prep_solution_fk")
prep_entries = prep_records
existing_record = next((r for r in prep_entries if r.get("Solution ID (FK)", "") == selected_solution_fk), None)
if existing_record:
    st.info("⚠️ Existing prep entry found. Fields prefilled for update.")
else:
    st.success("✅ No prep entry found. Enter new details.")

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
        value=float(safe_get(existing_record, "Solvent Weight Measured (g)", 0.0)), format="%.2f"
    )
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'],
        index=['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(safe_get(existing_record, "Polymer", "CMS-72")) if existing_record else 0
    )
    polymer_conc = st.number_input("Polymer starting concentration (%)",
        value=float(safe_get(existing_record, "Polymer starting concentration", 0.0)), format="%.2f"
    )
    polymer_lot = st.text_input("Polymer Lot Number", value=safe_get(existing_record, "Polymer Lot Number", ""))
    polymer_weight = st.number_input("Polymer Weight Measured (g)",
        value=float(safe_get(existing_record, "Polymer Weight Measured (g)", 0.0)), format="%.2f"
    )
    prep_date_str = safe_get(existing_record, "Prep Date")
    try:
        prep_date = datetime.strptime(prep_date_str, "%Y-%m-%d").date() if prep_date_str else datetime.today().date()
    except:
        prep_date = datetime.today().date()
    prep_date = st.date_input("Prep Date", value=prep_date)
    initials = st.text_input("Initials", value=safe_get(existing_record, "Initials", ""))
    notes = st.text_area("Notes", value=safe_get(existing_record, "Notes", ""))
    c_sol_conc_value = polymer_weight / (solvent_weight + polymer_weight) if (solvent_weight + polymer_weight) > 0 else 0.0
    st.markdown(
        f"""<div style="padding:8px 0 8px 0">
        <b>C-Solution Concentration <span style="font-weight:normal;">(polymer/(solvent+polymer)):</span></b>
        <code style="background:#E9F7EF; color:#247146; font-size:18px;">{c_sol_conc_value:.4f}</code>
        </div>""",
        unsafe_allow_html=True,
    )
    c_label_jar = st.text_input("C-Label for jar", value=safe_get(existing_record, "C-Label for jar", ""))
    submit_prep = st.form_submit_button("Submit/Update Prep Details")
if submit_prep:
    data = [
        prep_id, selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot,
        solvent_weight, polymer, polymer_conc, polymer_lot, polymer_weight, str(prep_date),
        initials, notes, c_sol_conc_value, c_label_jar
    ]
    try:
        if existing_record:
            cell = prep_sheet.find(selected_solution_fk)
            row_number = cell.row
            prep_sheet.update(f"A{row_number}:P{row_number}", [data])
            sol_row = df_solution[df_solution["Solution ID"]==selected_solution_fk].index[0] + 2
            solution_sheet.update(f"E{sol_row}", [[c_sol_conc_value]])
            st.cache_data.clear()
            st.success(":white_check_mark: Prep Data updated! Dropdowns and tables updated.")
            st.experimental_rerun()
        else:
            prep_sheet.append_row(data)
            sol_row = df_solution[df_solution["Solution ID"]==selected_solution_fk].index[0] + 2
            solution_sheet.update(f"E{sol_row}", [[c_sol_conc_value]])
            st.cache_data.clear()
            st.success(":white_check_mark: Prep Data submitted! Dropdowns and tables updated.")
            st.experimental_rerun()
    except Exception as e:
        st.error(f":x: Error while writing to Google Sheet: {e}")

# Reload after rerun for freshest data
solution_records = cached_get_all_records(SPREADSHEET_KEY, "Solution ID Tbl")
df_solution = pd.DataFrame(solution_records)
df_solution["Label"] = df_solution.apply(label_status, axis=1)
prep_records = cached_get_all_records(SPREADSHEET_KEY, "Solution Prep Data Tbl")
combined_records = cached_get_all_records(SPREADSHEET_KEY, "Combined Solution Tbl")

# --------------------- COMBINED SOLUTION ENTRY -----------------------
st.markdown("---")
st.markdown("## 🔹 Combined Solution Entry")

combined_ids_df = df_solution[
    (df_solution["Type"] == "Combined") &
    ((df_solution["Consumed"] == "No") | (df_solution["Expired"] == "No"))
]
combined_ids = combined_ids_df["Solution ID"].tolist()
if combined_ids:
    st.info("Active Combined Solution IDs: " + ", ".join(combined_ids))
else:
    st.info("No active Combined Solution IDs.")

valid_comb_df = df_solution[
    (df_solution["Type"] == "Combined") &
    ((df_solution['Consumed'] == "No") | (df_solution['Expired'] == "No"))
]
valid_comb_ids = valid_comb_df["Solution ID"].unique().tolist()

solution_options = []
sid_to_conc = {}
for sid in valid_comb_ids:
    preps = [p for p in prep_records if p.get("Solution ID (FK)", "") == sid]
    c = 0.0
    if preps:
        preps = sorted(preps, key=lambda p: parse_date(p.get("Prep Date", "")) or datetime.min, reverse=True)
        latest_prep = preps[0]
        c = float(latest_prep.get("C-Solution Concentration", 0) or 0)
    label = f"{sid} | Conc: {c:.4f}"
    solution_options.append(label)
    sid_to_conc[sid] = c

existing_comb_ids = [rec.get("Combined Solution ID") for rec in combined_records if rec.get("Combined Solution ID")]
combined_id = get_last_id_from_records(existing_comb_ids, "COMB")

with st.form("combined_solution_form", clear_on_submit=True):
    st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
    st.markdown("**Select Solution IDs to Combine:**")
    solution_id_a = st.selectbox("Solution ID A", options=solution_options, key="comb_a")
    solution_id_b = st.selectbox(
        "Solution ID B",
        options=[x for x in solution_options if x != solution_id_a],
        key="comb_b"
    )
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    sid_a = solution_id_a.split(" |")[0]
    sid_b = solution_id_b.split(" |")[0]
    conc_a = sid_to_conc.get(sid_a, 0)
    conc_b = sid_to_conc.get(sid_b, 0)
    combined_mass = solution_mass_a + solution_mass_b
    combined_conc = ((solution_mass_a * conc_a) + (solution_mass_b * conc_b)) / combined_mass if combined_mass > 0 else 0.0
    st.markdown(f"**Combined Solution Concentration (calculated):** `{combined_conc:.4f}`")
    st.warning("Check with your team: Do you ever combine different concentrations? This form will auto-calculate if you do.")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Initials")
    combined_notes = st.text_area("Notes")
    submit_combined = st.form_submit_button("Submit Combined Solution Details")
if submit_combined:
    combined_sheet.append_row([
        combined_id, sid_a, sid_b,
        solution_mass_a, solution_mass_b, combined_conc,
        str(combined_date), combined_initials, combined_notes
    ])
    st.cache_data.clear()
    st.success(":white_check_mark: Combined Solution saved! Dropdowns and tables updated.")
    st.experimental_rerun()

# ----------- 7-Day Recent Data Section (all activities) -----------
st.markdown("---")
st.markdown("## 📅 Last 7 Days Data Preview")

today = datetime.today()
recent_prep_ids = [
    rec for rec in prep_records
    if (parsed := parse_date(rec.get("Prep Date", ""))) and parsed >= today - timedelta(days=7)
]
recent_combined = [
    rec for rec in combined_records
    if (cd := parse_date(rec.get("Combined Date", rec.get("Date", "")))) and cd >= today - timedelta(days=7)
]
recent_solution_ids = set(rec.get("Solution ID (FK)", "").strip() for rec in recent_prep_ids)
recent_solution_ids.update(rec.get("Solution ID A", "").strip() for rec in recent_combined)
recent_solution_ids.update(rec.get("Solution ID B", "").strip() for rec in recent_combined)

st.markdown("### Solution ID Table (Filtered by Recent Activity)")
filtered_solution_ids = [rec for rec in solution_records if rec.get("Solution ID", "").strip() in recent_solution_ids]
if filtered_solution_ids:
    st.dataframe(pd.DataFrame(filtered_solution_ids))
else:
    st.write("No recent Solution ID records based on activity.")

st.markdown("### Solution Prep Data (Last 7 Days Only)")
if recent_prep_ids:
    st.dataframe(pd.DataFrame(recent_prep_ids))
else:
    st.write("No Solution Prep records in the last 7 days.")

st.markdown("### Combined Solution Data (Last 7 Days Only)")
if recent_combined:
    st.dataframe(pd.DataFrame(recent_combined))
else:
    st.write("No Combined Solution records in the last 7 days.")
