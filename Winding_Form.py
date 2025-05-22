# ----------------- WINDING FORM WITH PREFILL + DUPLICATE CHECK -----------------
# 📅 Season 2 Update – May 2025

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
TAB_WRAP_PER_MODULE = "Wrap per Module Tbl"
TAB_SPOOLS_PER_WIND = "Spools per Wind Tbl"

# ----------------- UTILS -----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(sheet, tab_name, headers):
    clean_tab_name = tab_name.strip().lower()
    for ws in sheet.worksheets():
        if ws.title.strip().lower() == clean_tab_name:
            return ws
    worksheet = sheet.add_worksheet(title=tab_name.strip(), rows="1000", cols="50")
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
    return [r for r in records if date_key in r and r[date_key] and \
            datetime.strptime(r[date_key], "%Y-%m-%d").date() >= (today - timedelta(days=7)).date()]

# ----------------- CONNECT SHEETS -----------------
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

# ----------------- WIND PROGRAM FORM -----------------
st.subheader("🌬️ Wind Program Entry")
wind_program_data = pd.DataFrame(wind_program_sheet.get_all_records())
selected_wp_id = st.selectbox("Select Wind Program ID to View/Edit", [""] + wind_program_ids)

wp_prefill = wind_program_data[wind_program_data["Wind Program ID"] == selected_wp_id].iloc[0] if selected_wp_id and selected_wp_id in wind_program_data["Wind Program ID"].values else None

with st.form("wind_program_form", clear_on_submit=True):
    wind_program_id = selected_wp_id or get_last_id(wind_program_sheet, "WP")
    st.markdown(f"**Wind Program ID:** `{wind_program_id}`")

    program_name = st.text_input("Program Name", value=wp_prefill["Program Name"] if wp_prefill is not None else "")
    bundles = st.number_input("Number of Bundles / Wind", min_value=0, step=1, value=int(wp_prefill["Number of bundles / wind"]) if wp_prefill is not None else 0)
    fibers_per_ribbon = st.number_input("Number of Fibers / Ribbon", min_value=0, step=1, value=int(wp_prefill["Number of fibers / ribbon"]) if wp_prefill is not None else 0)
    spacing = st.number_input("Space Between Ribbons", min_value=0.0, step=0.1, value=float(wp_prefill["Space between ribbons"]) if wp_prefill is not None else 0.0)
    wind_angle = st.number_input("Wind Angle (deg)", min_value=0, step=1, value=int(wp_prefill["Wind Angle (deg)"]) if wp_prefill is not None else 0)
    active_length = st.number_input("Active Fiber Length (inch)", min_value=0.0, value=float(wp_prefill["Active fiber length (inch)"]) if wp_prefill is not None else 0.0)
    total_length = st.number_input("Total Fiber Length (inch)", min_value=0.0, value=float(wp_prefill["Total fiber length (inch)"]) if wp_prefill is not None else 0.0)
    active_area = st.number_input("Active Area / Fiber", min_value=0.0, value=float(wp_prefill["Active Area / fiber"]) if wp_prefill is not None else 0.0)
    layers = st.number_input("Number of Layers", min_value=0, step=1, value=int(wp_prefill["Number of layers"]) if wp_prefill is not None else 0)
    loops_per_layer = st.number_input("Number of Loops / Layer", min_value=0, step=1, value=int(wp_prefill["Number of loops / layer"]) if wp_prefill is not None else 0)
    area_layer = st.number_input("C - Active Area / Layer", min_value=0.0, value=float(wp_prefill["C - Active area / layer"]) if wp_prefill is not None else 0.0)
    notes = st.text_area("Notes", value=wp_prefill["Notes"] if wp_prefill is not None else "")
    wind_submit = st.form_submit_button("💾 Save Wind Program")

if wind_submit:
    new_entry = [wind_program_id, program_name, bundles, fibers_per_ribbon, spacing, wind_angle, active_length, total_length, active_area, layers, loops_per_layer, area_layer, notes]
    if selected_wp_id and selected_wp_id in wind_program_data["Wind Program ID"].values:
        idx = wind_program_data[wind_program_data["Wind Program ID"] == selected_wp_id].index[0] + 2
        wind_program_sheet.delete_rows(idx)
        wind_program_sheet.insert_row(new_entry, idx)
        st.success(f"✅ Wind Program `{wind_program_id}` updated.")
    else:
        wind_program_sheet.append_row(new_entry)
        st.success(f"✅ Wind Program `{wind_program_id}` saved.")

# ----------------- DUPLICATE CHECK FOR WOUND MODULE ID -----------------
wound_data = pd.DataFrame(wound_module_sheet.get_all_records())
latest_id = get_last_id(wound_module_sheet, "WMOD")
if latest_id in wound_data["Wound Module ID"].values:
    st.warning(f"⚠️ Wound Module ID `{latest_id}` already exists. Consider reviewing existing entries.")
