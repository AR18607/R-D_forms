import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets API setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
spreadsheet = client.open("R&D Data Form")

# Helper: Create or fetch worksheet
def get_or_create_worksheet(sheet, title, headers):
    try:
        worksheet = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=title, rows="1000", cols="50")
        worksheet.append_row(headers)
    return worksheet

# Helper: Generate auto-incrementing ID
def get_next_id(worksheet, id_column):
    records = worksheet.get_all_records()
    if records:
        last_id = max([int(record[id_column]) for record in records if str(record[id_column]).isdigit()])
        return last_id + 1
    else:
        return 1

# -- Reference sheets for dropdowns
module_sheet = spreadsheet.worksheet("Module Tbl")
module_ids = [record["Module_ID"] for record in module_sheet.get_all_records()]

coated_spool_sheet = spreadsheet.worksheet("Coated Spool Tbl")
coated_spool_ids = [record["CoatedSpool_ID"] for record in coated_spool_sheet.get_all_records()]

wind_program_sheet = spreadsheet.worksheet("Wind Program Tbl")
wind_program_ids = [record["Wind_Program_ID"] for record in wind_program_sheet.get_all_records()]

# -------------------- Wind Program Tbl --------------------
st.header("Wind Program Entry")

wind_headers = [
    "Wind_Program_ID", "Program_Name", "Number_of_Bundles", "Number_of_Fibers_Per_Ribbon",
    "Space_Between_Ribbons", "Wind_Angle", "Active_Fiber_Length", "Total_Fiber_Length",
    "Active_Area_Fiber", "Number_of_Layers", "Number_of_Loops_Per_Layer", "Active_Area_Layer", "Notes"
]
wind_sheet = get_or_create_worksheet(spreadsheet, "Wind Program Tbl", wind_headers)

with st.form("Wind Program Form"):
    program_name = st.text_input("Program Name")
    num_bundles = st.number_input("Number of Bundles / Wind", min_value=0)
    num_fibers = st.number_input("Number of Fibers / Ribbon", min_value=0)
    spacing = st.number_input("Space Between Ribbons", min_value=0.0)
    wind_angle = st.number_input("Wind Angle (deg)", min_value=0.0)
    active_len = st.number_input("Active Fiber Length (inch)", min_value=0.0)
    total_len = st.number_input("Total Fiber Length (inch)", min_value=0.0)
    active_area = st.number_input("Active Area / Fiber", min_value=0.0)
    layers = st.number_input("Number of Layers", min_value=0)
    loops = st.number_input("Number of Loops / Layer", min_value=0)
    area_layer = st.number_input("C - Active Area / Layer", min_value=0.0)
    notes = st.text_area("Notes")
    
    submitted = st.form_submit_button("Submit")
    if submitted:
        wind_id = get_next_id(wind_sheet, "Wind_Program_ID")
        wind_sheet.append_row([
            wind_id, program_name, num_bundles, num_fibers, spacing, wind_angle,
            active_len, total_len, active_area, layers, loops, area_layer, notes
        ])
        st.success(f"Wind Program Entry with ID {wind_id} submitted successfully!")

# -------------------- Wound Module Tbl --------------------
st.header("Wound Module Entry")

wm_headers = [
    "Wound_Module_ID", "Module_ID", "Wind_Program_ID", "Operator_Initials", "Notes",
    "MFG_DB_Wind_ID", "MFG_DB_Potting_ID", "MFG_DB_Mod_ID"
]
wm_sheet = get_or_create_worksheet(spreadsheet, "Wound Module Tbl", wm_headers)

with st.form("Wound Module Form"):
    selected_module_id = st.selectbox("Module ID", module_ids)
    selected_wind_prog_id = st.selectbox("Wind Program ID", wind_program_ids)
    operator = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    mfg_wind_id = st.text_input("MFG DB Wind ID")
    mfg_potting_id = st.text_input("MFG DB Potting ID")
    mfg_mod_id = st.number_input("MFG DB Mod ID", min_value=0)
    
    submitted = st.form_submit_button("Submit")
    if submitted:
        wound_mod_id = get_next_id(wm_sheet, "Wound_Module_ID")
        wm_sheet.append_row([
            wound_mod_id, selected_module_id, selected_wind_prog_id, operator, notes,
            mfg_wind_id, mfg_potting_id, mfg_mod_id
        ])
        st.success(f"Wound Module Entry with ID {wound_mod_id} submitted successfully!")

# -------------------- Wrap per Module Tbl --------------------
st.header("Wrap per Module Entry")

wrap_headers = ["WrapPerModule_PK", "Module_ID", "Wrap_After_Layer", "Type_of_Wrap", "Notes"]
wrap_sheet = get_or_create_worksheet(spreadsheet, "Wrap per Module Tbl", wrap_headers)

with st.form("Wrap per Module Form"):
    selected_module_id = st.selectbox("Module ID (Wrap)", module_ids)
    wrap_after_layer = st.number_input("Wrap After Layer #", min_value=0)
    wrap_type = st.text_input("Type of Wrap")
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        wrap_pk = get_next_id(wrap_sheet, "WrapPerModule_PK")
        wrap_sheet.append_row([wrap_pk, selected_module_id, wrap_after_layer, wrap_type, notes])
        st.success(f"Wrap Per Module Entry with ID {wrap_pk} submitted successfully!")

# -------------------- Spools per Wind Tbl --------------------
st.header("Spools per Wind Entry")

spw_headers = ["SpoolPerWind_PK", "MFG_DB_Wind_ID", "Coated_Spool_ID", "Length_Used", "Notes"]
spw_sheet = get_or_create_worksheet(spreadsheet, "Spools per Wind Tbl", spw_headers)

with st.form("Spools per Wind Form"):
    mfg_wind_id = st.text_input("MFG DB Wind ID")
    selected_coated_spool = st.selectbox("Coated Spool ID", coated_spool_ids)
    length_used = st.number_input("Length Used", min_value=0.0)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        spw_pk = get_next_id(spw_sheet, "SpoolPerWind_PK")
        spw_sheet.append_row([spw_pk, mfg_wind_id, selected_coated_spool, length_used, notes])
        st.success(f"Spools per Wind Entry with ID {spw_pk} submitted successfully!")
