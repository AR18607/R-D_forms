# 🧪 Mini Module Entry Form – Updated Version with Edits

import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MINI_MODULE = "Mini Module Tbl"
TAB_MODULE = "Module Tbl"
TAB_BATCH_FIBER = "Batch Fiber Tbl"
TAB_UNCOATED_SPOOL = "Uncoated Spool Tbl"
TAB_COATED_SPOOL = "Coated Spool Tbl"
TAB_DCOATING = "Dcoating Tbl"

# ------------------ CONNECT GOOGLE SHEET ------------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        if len(worksheet.row_values(1)) == 0:
            worksheet.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def generate_c_module_label(operator_initials):
    today = datetime.today().strftime("%Y%m%d")
    base_label = today + operator_initials.upper()
    existing_labels = mini_sheet.col_values(11)[1:]  # 11th column is Module Label
    sequence = [l.replace(base_label, '') for l in existing_labels if l.startswith(base_label)]
    if sequence:
        letters = sorted(sequence)
        next_letter = chr(ord(letters[-1]) + 1)
    else:
        next_letter = 'A'
    return base_label + next_letter

def filter_last_7_days(df):
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df[df["Date"] >= datetime.today() - timedelta(days=7)]

# ------------------ LOAD SHEETS ------------------
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
mini_sheet = get_or_create_tab(spreadsheet, TAB_MINI_MODULE, [
    "Mini Module ID", "Module ID", "Batch Fiber ID", "UncoatedSpool ID", "CoatedSpool ID", "Dcoating ID",
    "Number of Fibers", "Fiber Length", "Active Area", "Operator Initials", "Module Label", "Notes", "Date"])
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
batch_fiber_sheet = get_or_create_tab(spreadsheet, TAB_BATCH_FIBER, ["Batch Fiber ID"])
uncoated_spool_sheet = get_or_create_tab(spreadsheet, TAB_UNCOATED_SPOOL, ["UncoatedSpool ID"])
coated_spool_sheet = get_or_create_tab(spreadsheet, TAB_COATED_SPOOL, ["CoatedSpool_ID"])
dcoating_sheet = get_or_create_tab(spreadsheet, TAB_DCOATING, ["Dcoating ID"])

# ------------------ DROPDOWNS ------------------
mini_df = pd.DataFrame(mini_sheet.get_all_records())
module_df = pd.DataFrame(module_sheet.get_all_records())
existing_modules = module_df[module_df["Module Type"] == "Mini Module"]["Module ID"].tolist()
batch_fiber_ids = batch_fiber_sheet.col_values(1)[1:]
uncoated_spool_ids = uncoated_spool_sheet.col_values(1)[1:]
coated_spool_ids = coated_spool_sheet.col_values(1)[1:]
dcoating_ids = dcoating_sheet.col_values(1)[1:]

st.title("🧪 Mini Module Entry Form")

with st.form("mini_module_form"):
    st.subheader("🔹 Mini Module Entry")
    selected_module = st.selectbox("Module ID (Mini only)", existing_modules)
    prefill_row = mini_df[mini_df["Module ID"] == selected_module].iloc[0] if selected_module in mini_df["Module ID"].values else None

    mini_module_id = prefill_row["Mini Module ID"] if prefill_row is not None else get_last_id(mini_sheet, "MINIMOD")
    st.markdown(f"**Mini Module ID:** `{mini_module_id}`")

    batch_fiber_id = st.selectbox("Batch Fiber ID", batch_fiber_ids, index=0 if prefill_row is None else batch_fiber_ids.index(prefill_row["Batch Fiber ID"]))
    uncoated_spool_id = st.selectbox("Uncoated Spool ID", uncoated_spool_ids, index=0 if prefill_row is None else uncoated_spool_ids.index(prefill_row["UncoatedSpool ID"]))
    coated_spool_id = st.selectbox("Coated Spool ID", coated_spool_ids, index=0 if prefill_row is None else coated_spool_ids.index(prefill_row["CoatedSpool ID"]))
    dcoating_id = st.selectbox("Dcoating ID", dcoating_ids, index=0 if prefill_row is None else dcoating_ids.index(prefill_row["Dcoating ID"]))

    number_of_fibers = st.number_input("Number of Fibers", step=1, value=0 if prefill_row is None else int(prefill_row["Number of Fibers"]))
    fiber_length = st.number_input("Fiber Length (inches)", format="%.2f", value=0.0 if prefill_row is None else float(prefill_row["Fiber Length"]))
    active_area = st.number_input("C - Active Area", format="%.2f", value=0.0 if prefill_row is None else float(prefill_row["Active Area"]))
    operator_initials = st.text_input("Operator Initials", value="" if prefill_row is None else prefill_row["Operator Initials"])

    auto_generate_label = st.checkbox("Auto-generate C-Module Label?", value=True)
    module_label = generate_c_module_label(operator_initials) if auto_generate_label and operator_initials else st.text_input("C-Module Label", value="" if prefill_row is None else prefill_row["Module Label"])
    notes = st.text_area("Notes", value="" if prefill_row is None else prefill_row["Notes"])
    date_today = st.date_input("Date", value=datetime.today().date() if prefill_row is None else datetime.strptime(prefill_row["Date"], "%Y-%m-%d").date())

    submit = st.form_submit_button("💾 Save Entry")

if submit:
    try:
        updated_row = [mini_module_id, selected_module, batch_fiber_id, uncoated_spool_id, coated_spool_id,
                       dcoating_id, number_of_fibers, fiber_length, active_area, operator_initials,
                       module_label, notes, str(date_today)]
        if prefill_row is not None:
            idx = mini_df[mini_df["Mini Module ID"] == mini_module_id].index[0] + 2
            mini_sheet.delete_rows(idx)
            mini_sheet.insert_row(updated_row, idx)
            st.success("✅ Entry updated successfully!")
        else:
            mini_sheet.append_row(updated_row)
            st.success("✅ Mini Module entry saved successfully!")
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")

# ------------------ 7-DAY REVIEW ------------------
st.subheader("📅 Recent Mini Module Entries (Last 7 Days)")
if not mini_df.empty:
    recent = filter_last_7_days(mini_df)
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No entries in the last 7 days.")
else:
    st.info("No data found.")
