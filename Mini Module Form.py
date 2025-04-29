import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ CONFIG ------------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MINI_MODULE = "Mini Module Tbl"
TAB_MODULE = "Module Tbl"

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
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]  # skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def generate_c_module_label(operator_initials):
    today = datetime.today().strftime("%Y%m%d")
    base_label = today + operator_initials.upper()

    # Fetch existing labels starting with today+initials
    existing_labels = mini_sheet.col_values(10)[1:]  # 10th column is Module Label (adjust if needed)
    sequence = [l.replace(base_label, '') for l in existing_labels if l.startswith(base_label)]

    if sequence:
        # Find next letter
        letters = sorted(sequence)
        next_letter = chr(ord(letters[-1]) + 1)
    else:
        next_letter = 'A'

    return base_label + next_letter

# ------------------ MAIN FORM ------------------

st.title("🧪 Mini Module Entry Form")

# Connect
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
mini_sheet = get_or_create_tab(spreadsheet, TAB_MINI_MODULE, [
    "Mini Module ID", "Module ID", "Batch Fiber ID", "UncoatedSpool ID", "CoatedSpool ID", "Dcoating ID",
    "Number of Fibers", "Fiber Length", "Active Area", "Operator Initials", "Module Label", "Notes", "Date"
])
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])

# Fetch existing FKs
existing_modules = module_sheet.col_values(1)[1:]

# Form
with st.form("mini_module_form"):

    st.subheader("🔹 Mini Module Entry")

    mini_module_id = get_last_id(mini_sheet, "MINIMOD")
    st.markdown(f"**Auto-generated Mini Module ID:** `{mini_module_id}`")

    # Dropdowns for foreign keys
    module_fk = st.selectbox("Module ID (from Module Tbl)", existing_modules) if existing_modules else st.text_input("Module ID (manual)")

    batch_fiber_id = st.text_input("Batch Fiber ID (optional)")
    uncoated_spool_id = st.text_input("Uncoated Spool ID (optional)")
    coated_spool_id = st.text_input("Coated Spool ID (optional)")
    dcoating_id = st.text_input("Dcoating ID (optional)")

    number_of_fibers = st.number_input("Number of Fibers", step=1)
    fiber_length = st.number_input("Fiber Length (inches)", format="%.2f")
    active_area = st.number_input("C - Active Area", format="%.2f")
    operator_initials = st.text_input("Operator Initials")

    auto_generate_label = st.checkbox("Auto-generate C-Module Label?", value=True)

    if auto_generate_label and operator_initials:
        module_label = generate_c_module_label(operator_initials)
        st.markdown(f"**Generated Label:** `{module_label}`")
    else:
        module_label = st.text_input("Manually Enter C-Module Label")

    notes = st.text_area("Notes")
    date_today = st.date_input("Date")

    submit = st.form_submit_button("🚀 Submit")

# ------------------ SAVE ------------------

if submit:
    try:
        mini_sheet.append_row([
            mini_module_id,
            module_fk,
            batch_fiber_id,
            uncoated_spool_id,
            coated_spool_id,
            dcoating_id,
            number_of_fibers,
            fiber_length,
            active_area,
            operator_initials,
            module_label,
            notes,
            str(date_today)
        ])
        st.success("✅ Mini Module entry saved successfully!")
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")
