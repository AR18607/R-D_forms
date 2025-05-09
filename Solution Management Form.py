# This is a modular refactor of your existing code with enhancements applied
import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# Config
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_SOLUTION_ID = "Solution ID Tbl"
TAB_SOLUTION_PREP = "Solution Prep Data Tbl"
TAB_COMBINED_SOLUTION = "Combined Solution Tbl"

# Google Sheets Auth
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, id_prefix):
    ids = worksheet.col_values(1)[1:]
    if not ids: return f"{id_prefix}-001"
    nums = [int(i.split('-')[-1]) for i in ids if i.startswith(id_prefix)]
    return f"{id_prefix}-{str(max(nums)+1).zfill(3)}"

# Launch
st.title("🧪 Solution Management")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
solution_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_ID, ["Solution ID", "Type", "Expired", "Consumed"])
prep_sheet = get_or_create_tab(spreadsheet, TAB_SOLUTION_PREP, [
    "Solution Prep ID", "Solution ID (FK)", "Desired Solution Concentration", "Desired Final Volume",
    "Solvent", "Solvent Lot Number", "Solvent Weight Measured (g)", "Polymer", "Polymer starting concentration",
    "Polymer Lot Number", "Polymer Weight Measured (g)", "Prep Date", "Initials", "Notes",
    "C-Solution Concentration", "C-Label for jar"
])
combined_sheet = get_or_create_tab(spreadsheet, TAB_COMBINED_SOLUTION, [
    "Combined Solution ID", "Solution ID (FK)", "Solution Prep ID (FK)", "Solution Mass",
    "Date", "Initials", "Notes", "C-Label for jar"
])

# Fetch Existing IDs
solution_ids = solution_sheet.col_values(1)[1:]
prep_ids = prep_sheet.col_values(1)[1:]

# --- 🔹 FORM 1: Solution ID Entry ---
with st.form("form_solution_id"):
    st.subheader("🔹 Add New Solution ID")
    new_solution_id = get_last_id(solution_sheet, "SOL")
    st.markdown(f"🆔 Auto-ID: `{new_solution_id}`")
    sol_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['No', 'Yes'])
    consumed = st.selectbox("Consumed?", ['No', 'Yes'])
    submit_id = st.form_submit_button("➕ Submit Solution ID")
    if submit_id:
        solution_sheet.append_row([new_solution_id, sol_type, expired, consumed])
        st.success(f"✅ Added Solution ID `{new_solution_id}`")

# --- 🔸 FORM 2: Solution Prep Entry ---
with st.form("form_prep"):
    st.subheader("🔸 Prepare Solution")
    prep_id = get_last_id(prep_sheet, "PREP")
    st.markdown(f"🧪 Auto-Prep ID: `{prep_id}`")
    solution_fk = st.selectbox("Select Existing Solution ID", solution_ids)
    
    existing_prep = prep_sheet.get_all_records()
    prefill = next((row for row in existing_prep if row["Solution ID (FK)"] == solution_fk), None)

    if prefill:
        st.warning("⚠️ This Solution ID has a prep entry. Submitting will overwrite.")
    
    desired_conc = st.number_input("Desired Concentration (%)", value=prefill["Desired Solution Concentration"] if prefill else 0.0)
    final_vol = st.number_input("Final Volume", value=prefill["Desired Final Volume"] if prefill else 0.0)
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'])
    solvent_lot = st.text_input("Solvent Lot", value=prefill["Solvent Lot Number"] if prefill else "")
    solvent_wt = st.number_input("Solvent Weight (g)", value=prefill["Solvent Weight Measured (g)"] if prefill else 0.0)
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'])
    polymer_conc = st.number_input("Polymer Start Conc (%)", value=prefill["Polymer starting concentration"] if prefill else 0.0)
    polymer_lot = st.text_input("Polymer Lot", value=prefill["Polymer Lot Number"] if prefill else "")
    polymer_wt = st.number_input("Polymer Weight (g)", value=prefill["Polymer Weight Measured (g)"] if prefill else 0.0)
    prep_date = st.date_input("Date", value=datetime.today())
    initials = st.text_input("Initials", value=prefill["Initials"] if prefill else "")
    notes = st.text_area("Notes", value=prefill["Notes"] if prefill else "")
    c_conc = st.number_input("C-Solution Conc", value=prefill["C-Solution Concentration"] if prefill else 0.0)
    c_label = st.text_input("C-Label", value=prefill["C-Label for jar"] if prefill else "")

    submit_prep = st.form_submit_button("🧪 Save/Update Solution Prep")

    if submit_prep:
        if prefill:
            row_index = next(i for i, r in enumerate(prep_sheet.get_all_values()) if r[1] == solution_fk)
            prep_sheet.delete_row(row_index + 1)
        prep_sheet.append_row([
            prep_id, solution_fk, desired_conc, final_vol, solvent, solvent_lot,
            solvent_wt, polymer, polymer_conc, polymer_lot, polymer_wt,
            str(prep_date), initials, notes, c_conc, c_label
        ])
        st.success("✅ Solution prep data saved.")

# --- 🔻 FORM 3: Combine Solutions ---
with st.form("form_combine"):
    st.subheader("🔻 Combine Solution Batches")
    combined_id = get_last_id(combined_sheet, "COMB")
    st.markdown(f"🧬 Auto-ID: `{combined_id}`")
    comb_solution_fk = st.selectbox("Solution ID", solution_ids, key="comb_sol")
    comb_prep_fk = st.selectbox("Prep ID", prep_ids, key="comb_prep")
    comb_mass = st.number_input("Solution Mass (g)")
    comb_date = st.date_input("Date", value=datetime.today())
    comb_initials = st.text_input("Initials")
    comb_notes = st.text_area("Notes")
    comb_label = st.text_input("C-Label")

    submit_comb = st.form_submit_button("🧬 Submit Combined Entry")

    if submit_comb:
        combined_sheet.append_row([
            combined_id, comb_solution_fk, comb_prep_fk, comb_mass,
            str(comb_date), comb_initials, comb_notes, comb_label
        ])
        st.success(f"✅ Combined entry `{combined_id}` saved.")

# --- 🔍 7-Day Review ---
st.markdown("### 📅 Recent Entries (Last 7 Days)")

today = datetime.today()
cutoff = today - timedelta(days=7)

def show_recent_entries(sheet, label):
    df = pd.DataFrame(sheet.get_all_records())
    if "Prep Date" in df.columns:
        df["Prep Date"] = pd.to_datetime(df["Prep Date"], errors='coerce')
        df = df[df["Prep Date"] >= cutoff]
    elif "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df[df["Date"] >= cutoff]
    if not df.empty:
        st.write(f"#### 🗃 {label}")
        st.dataframe(df)
    else:
        st.info(f"No recent data found in {label}")

show_recent_entries(solution_sheet, "Solution IDs")
show_recent_entries(prep_sheet, "Solution Preps")
show_recent_entries(combined_sheet, "Combined Solutions")
