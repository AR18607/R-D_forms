import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# -------------- GOOGLE SHEET CONFIG --------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_WOUND_MODULE = "Wound Module Tbl"
TAB_WRAP_MODULE = "Wrap per Module Tbl"
TAB_SPOOLS_WIND = "Spools per Wind Tbl"
TAB_WIND_PROGRAM = "Wind Program Tbl"

# -------------- GOOGLE CONNECTION --------------
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
    records = worksheet.col_values(1)[1:]  # Skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

# -------------- APP STARTS --------------

st.title("🌀 Winding Form (4 Tables Connected)")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Sheets
sheet_wound_module = get_or_create_tab(spreadsheet, TAB_WOUND_MODULE, [
    "Wound Module ID", "Module ID", "Wind Program ID", "Operator Initials", "Notes",
    "MFG DB Wind ID", "MFG DB Potting ID", "MFG DB Mod ID"
])

sheet_wrap_module = get_or_create_tab(spreadsheet, TAB_WRAP_MODULE, [
    "WrapPerModule PK", "Module ID", "Wrap After Layer", "Type of Wrap", "Notes"
])

sheet_spools_wind = get_or_create_tab(spreadsheet, TAB_SPOOLS_WIND, [
    "SpoolPerWind PK", "MFG DB Wind ID", "Coated Spool ID", "Length Used", "Notes"
])

sheet_wind_program = get_or_create_tab(spreadsheet, TAB_WIND_PROGRAM, [
    "Wind Program ID", "Program Name", "Number of bundles / wind", "Number of fibers / ribbon",
    "Space between ribbons", "Wind Angle (deg)", "Active fiber length (inch)",
    "Total fiber length (inch)", "Active Area / fiber", "Number of layers",
    "Number of loops / layer", "C - Active area / layer", "Notes"
])

# Form UI
with st.form("winding_full_form"):
    st.subheader("🔹 Wound Module Entry")
    wound_module_id = get_last_id(sheet_wound_module, "WMOD")
    st.markdown(f"**Auto-generated Wound Module ID:** `{wound_module_id}`")

    module_id = st.text_input("Module ID (from Module Tbl)")
    wind_program_id_fk = st.text_input("Wind Program ID (from Wind Program Tbl)")
    operator_initials = st.text_input("Operator Initials")
    notes_wound = st.text_area("Wound Module Notes")
    mfg_db_wind_id = st.text_input("MFG DB Wind ID")
    mfg_db_potting_id = st.text_input("MFG DB Potting ID")
    mfg_db_mod_id = st.number_input("MFG DB Mod ID", step=1)

    st.subheader("🔹 Wrap per Module Entry")
    wrap_module_pk = get_last_id(sheet_wrap_module, "WPM")
    st.markdown(f"**Auto-generated Wrap Per Module PK:** `{wrap_module_pk}`")

    wrap_module_id_fk = st.text_input("Module ID (Wrap)", value=module_id)
    wrap_after_layer = st.number_input("Wrap After Layer #", step=1)
    type_of_wrap = st.text_input("Type of Wrap")
    notes_wrap = st.text_area("Wrap Notes")

    st.subheader("🔹 Spools per Wind Entry")
    spools_wind_pk = get_last_id(sheet_spools_wind, "SPW")
    st.markdown(f"**Auto-generated Spool Per Wind PK:** `{spools_wind_pk}`")

    spools_mfg_db_wind_id = st.text_input("MFG DB Wind ID (Spool)", value=mfg_db_wind_id)
    coated_spool_id = st.number_input("Coated Spool ID", step=1)
    length_used = st.number_input("Length Used", format="%.2f")
    notes_spools = st.text_area("Spool Notes")

    st.subheader("🔹 Wind Program Entry")
    wind_program_id = get_last_id(sheet_wind_program, "WP")
    st.markdown(f"**Auto-generated Wind Program ID:** `{wind_program_id}`")

    program_name = st.text_input("Program Name")
    number_of_bundles = st.number_input("Number of bundles / wind", step=1)
    fibers_per_ribbon = st.number_input("Number of fibers / ribbon", step=1)
    space_between_ribbons = st.number_input("Space between ribbons", format="%.2f")
    wind_angle = st.number_input("Wind Angle (deg)", step=1)
    active_fiber_length = st.number_input("Active fiber length (inch)", format="%.2f")
    total_fiber_length = st.number_input("Total fiber length (inch)", format="%.2f")
    active_area_fiber = st.number_input("Active Area / fiber", format="%.2f")
    number_of_layers = st.number_input("Number of layers", step=1)
    loops_per_layer = st.number_input("Number of loops / layer", step=1)
    c_active_area_layer = st.number_input("C - Active area / layer", format="%.2f")
    notes_wind_prog = st.text_area("Wind Program Notes")

    submit_btn = st.form_submit_button("🚀 Submit All Winding Form Data")

# Save Data
if submit_btn:
    try:
        sheet_wound_module.append_row([
            wound_module_id, module_id, wind_program_id_fk, operator_initials,
            notes_wound, mfg_db_wind_id, mfg_db_potting_id, mfg_db_mod_id
        ])

        sheet_wrap_module.append_row([
            wrap_module_pk, wrap_module_id_fk, wrap_after_layer, type_of_wrap, notes_wrap
        ])

        sheet_spools_wind.append_row([
            spools_wind_pk, spools_mfg_db_wind_id, coated_spool_id, length_used, notes_spools
        ])

        sheet_wind_program.append_row([
            wind_program_id, program_name, number_of_bundles, fibers_per_ribbon,
            space_between_ribbons, wind_angle, active_fiber_length, total_fiber_length,
            active_area_fiber, number_of_layers, loops_per_layer, c_active_area_layer,
            notes_wind_prog
        ])

        st.success("✅ All Winding Form data successfully saved!")
    except Exception as e:
        st.error(f"❌ Failed to save data: {e}")
