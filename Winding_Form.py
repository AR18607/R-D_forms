# ----------------- WINDING FORM WITH UPDATES -----------------
# 📅 Season 2 Update – May 2025
# ✅ Updates: Submit behavior fixed, 7-day review added, clear submit buttons

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import pandas as pd

# ----------------- CONFIG -----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

TAB_MODULE = "Module Tbl"
TAB_WIND_PROGRAM = "Wind Program Tbl"
TAB_WOUND_MODULE = "Wound Module Tbl"
TAB_WRAP_PER_MODULE = "Wrap Per Module Tbl"
TAB_SPOOLS_PER_WIND = "Spools Per Wind Tbl"

# ----------------- UTILS -----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
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
    records = worksheet.col_values(1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def fetch_column_values(worksheet, col_index=1):
    values = worksheet.col_values(col_index)[1:]
    return [v for v in values if v]

def filter_last_7_days(records, date_key):
    today = datetime.today()
    filtered = []
    for record in records:
        date_str = record.get(date_key, "").strip()
        try:
            date_val = datetime.strptime(date_str, "%Y-%m-%d")
            if date_val.date() >= (today - timedelta(days=7)).date():
                filtered.append(record)
        except:
            continue
    return filtered

# ----------------- MAIN APP -----------------
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
wind_program_sheet = get_or_create_tab(spreadsheet, TAB_WIND_PROGRAM, [
    "Wind Program ID", "Program Name", "Number of bundles / wind", "Number of fibers / ribbon",
    "Space between ribbons", "Wind Angle (deg)", "Active fiber length (inch)", "Total fiber length (inch)",
    "Active Area / fiber", "Number of layers", "Number of loops / layer", "C - Active area / layer", "Notes"])
wound_module_sheet = get_or_create_tab(spreadsheet, TAB_WOUND_MODULE, [
    "Wound Module ID", "Module ID (FK)", "Wind Program ID (FK)", "Operator Initials", "Notes",
    "MFG DB Wind ID", "MFG DB Potting ID", "MFG DB Mod ID", "Date"])
wrap_per_module_sheet = get_or_create_tab(spreadsheet, TAB_WRAP_PER_MODULE, [
    "WrapPerModule PK", "Module ID (FK)", "Wrap After Layer #", "Type of Wrap", "Notes", "Date"])
spools_per_wind_sheet = get_or_create_tab(spreadsheet, TAB_SPOOLS_PER_WIND, [
    "SpoolPerWind PK", "MFG DB Wind ID (FK)", "Coated Spool ID", "Length Used", "Notes", "Date"])

module_ids = fetch_column_values(module_sheet)
wind_program_ids = fetch_column_values(wind_program_sheet)

st.title("🌀 Winding Form")

with st.form("winding_form", clear_on_submit=True):
    st.subheader("🔷 Wound Module Entry")
    wound_module_id = get_last_id(wound_module_sheet, "WMOD")
    st.markdown(f"**Auto-generated Wound Module ID:** `{wound_module_id}`")
    module_fk = st.selectbox("Module ID", module_ids)
    wind_program_fk = st.selectbox("Wind Program ID", wind_program_ids)
    operator_initials = st.text_input("Operator Initials")
    notes_wound = st.text_area("Wound Module Notes")
    mfg_db_wind = st.text_input("MFG DB Wind ID")
    mfg_db_potting = st.text_input("MFG DB Potting ID")
    mfg_db_mod = st.number_input("MFG DB Mod ID", step=1)

    st.subheader("🔷 Wrap Per Module Entry")
    wrap_per_module_pk = get_last_id(wrap_per_module_sheet, "WRAP")
    wrap_module_fk = st.selectbox("Module ID (Wrap)", module_ids)
    wrap_after_layer = st.number_input("Wrap After Layer #", step=1)
    type_of_wrap = st.text_input("Type of Wrap")
    wrap_notes = st.text_area("Wrap Notes")

    st.subheader("🔷 Spools Per Wind Entry")
    spool_per_wind_pk = get_last_id(spools_per_wind_sheet, "SPOOL")
    mfg_db_wind_fk = st.text_input("MFG DB Wind ID (FK)")
    coated_spool_id = st.text_input("Coated Spool ID")
    length_used = st.number_input("Length Used (m)", format="%.2f")
    spool_notes = st.text_area("Spool Notes")

    submit_button = st.form_submit_button("🚀 Save Winding Records")

if submit_button:
    now = datetime.now().strftime("%Y-%m-%d")
    wound_module_sheet.append_row([
        wound_module_id, module_fk, wind_program_fk, operator_initials, notes_wound,
        mfg_db_wind, mfg_db_potting, mfg_db_mod, now])
    wrap_per_module_sheet.append_row([
        wrap_per_module_pk, wrap_module_fk, wrap_after_layer, type_of_wrap, wrap_notes, now])
    spools_per_wind_sheet.append_row([
        spool_per_wind_pk, mfg_db_wind_fk, coated_spool_id, length_used, spool_notes, now])
    st.success("✅ All winding records saved!")

st.subheader("🌬️ Wind Program Entry")
with st.form("wind_program_form", clear_on_submit=True):
    wind_program_id = get_last_id(wind_program_sheet, "WP")
    st.markdown(f"**Auto-generated Wind Program ID:** `{wind_program_id}`")
    program_name = st.text_input("Program Name")
    bundles = st.number_input("Number of Bundles / Wind", min_value=0, step=1)
    fibers_per_ribbon = st.number_input("Number of Fibers / Ribbon", min_value=0, step=1)
    spacing = st.number_input("Space Between Ribbons", min_value=0.0, step=0.1)
    wind_angle = st.number_input("Wind Angle (deg)", min_value=0, step=1)
    active_length = st.number_input("Active Fiber Length (inch)", min_value=0.0)
    total_length = st.number_input("Total Fiber Length (inch)", min_value=0.0)
    active_area = st.number_input("Active Area / Fiber", min_value=0.0)
    layers = st.number_input("Number of Layers", min_value=0, step=1)
    loops_per_layer = st.number_input("Number of Loops / Layer", min_value=0, step=1)
    area_layer = st.number_input("C - Active Area / Layer", min_value=0.0)
    notes = st.text_area("Notes")
    wind_submit = st.form_submit_button("➕ Save Wind Program")

if wind_submit:
    wind_program_sheet.append_row([
        wind_program_id, program_name, bundles, fibers_per_ribbon, spacing, wind_angle,
        active_length, total_length, active_area, layers, loops_per_layer, area_layer, notes
    ])
    st.success("✅ Wind program saved!")

# ----------------- LAST 7 DAYS REVIEW -----------------
st.markdown("## 📅 Recent Winding Entries (Last 7 Days)")
for sheet, title, date_key in [
    (wound_module_sheet, "🔷 Wound Modules", "Date"),
    (wrap_per_module_sheet, "🔷 Wrap Per Module", "Date"),
    (spools_per_wind_sheet, "🔷 Spools Per Wind", "Date")
]:
    try:
        records = sheet.get_all_records()
        recent = filter_last_7_days(records, date_key)
        if recent:
            st.markdown(f"### {title}")
            st.dataframe(pd.DataFrame(recent))
    except Exception as e:
        st.warning(f"⚠️ Could not load recent data from {title}: {e}")
