import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------- CONFIG -----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = st.secrets["gcp_service_account"]

# Sheet tabs
TAB_MODULE = "Module Tbl"
TAB_WIND_PROGRAM = "Wind Program Tbl"
TAB_WOUND_MODULE = "Wound Module Tbl"
TAB_WRAP_PER_MODULE = "Wrap Per Module Tbl"
TAB_SPOOLS_PER_WIND = "Spools Per Wind Tbl"

# ----------------- CONNECT GOOGLE SHEETS -----------------
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
    records = worksheet.col_values(1)[1:]  # Skip header
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def fetch_column_values(worksheet, col_index=1):
    try:
        values = worksheet.col_values(col_index)[1:]  # Skip header
        return [v for v in values if v]
    except Exception:
        return []

# ----------------- MAIN APP -----------------
st.title("🌀 Winding Form (Connected)")

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Create/Connect tabs
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
wind_program_sheet = get_or_create_tab(spreadsheet, TAB_WIND_PROGRAM, [
    "Wind Program ID", "Program Name", "Number of bundles / wind", "Number of fibers / ribbon",
    "Space between ribbons", "Wind Angle (deg)", "Active fiber length (inch)", "Total fiber length (inch)",
    "Active Area / fiber", "Number of layers", "Number of loops / layer", "C - Active area / layer", "Notes"
])
wound_module_sheet = get_or_create_tab(spreadsheet, TAB_WOUND_MODULE, [
    "Wound Module ID", "Module ID (FK)", "Wind Program ID (FK)", "Operator Initials", "Notes",
    "MFG DB Wind ID", "MFG DB Potting ID", "MFG DB Mod ID"
])
wrap_per_module_sheet = get_or_create_tab(spreadsheet, TAB_WRAP_PER_MODULE, [
    "WrapPerModule PK", "Module ID (FK)", "Wrap After Layer #", "Type of Wrap", "Notes"
])
spools_per_wind_sheet = get_or_create_tab(spreadsheet, TAB_SPOOLS_PER_WIND, [
    "SpoolPerWind PK", "MFG DB Wind ID (FK)", "Coated Spool ID", "Length Used", "Notes"
])

# Fetch Dropdown Data
module_ids = fetch_column_values(module_sheet)
wind_program_ids = fetch_column_values(wind_program_sheet)

# Form
with st.form("winding_form"):
    st.subheader("🔷 Wound Module Entry")

    wound_module_id = get_last_id(wound_module_sheet, "WMOD")
    st.markdown(f"**Auto-generated Wound Module ID:** `{wound_module_id}`")

    module_fk = st.selectbox("Module ID", module_ids) if module_ids else st.text_input("Module ID (Manual)")
    wind_program_fk = st.selectbox("Wind Program ID", wind_program_ids) if wind_program_ids else st.text_input("Wind Program ID (Manual)")

    operator_initials = st.text_input("Operator Initials")
    notes_wound = st.text_area("Wound Module Notes")
    mfg_db_wind = st.text_input("MFG DB Wind ID")
    mfg_db_potting = st.text_input("MFG DB Potting ID")
    mfg_db_mod = st.number_input("MFG DB Mod ID", step=1)

    st.subheader("🔷 Wrap Per Module Entry")

    wrap_per_module_pk = get_last_id(wrap_per_module_sheet, "WRAP")
    st.markdown(f"**Auto-generated Wrap Per Module PK:** `{wrap_per_module_pk}`")

    wrap_module_fk = st.selectbox("Module ID (Wrap)", module_ids) if module_ids else st.text_input("Module ID (Wrap Manual)")
    wrap_after_layer = st.number_input("Wrap After Layer #", step=1)
    type_of_wrap = st.text_input("Type of Wrap")
    wrap_notes = st.text_area("Wrap Notes")

    st.subheader("🔷 Spools Per Wind Entry")

    spool_per_wind_pk = get_last_id(spools_per_wind_sheet, "SPOOL")
    st.markdown(f"**Auto-generated Spool Per Wind PK:** `{spool_per_wind_pk}`")

    mfg_db_wind_fk = st.text_input("MFG DB Wind ID (FK)")
    coated_spool_id = st.text_input("Coated Spool ID")
    length_used = st.number_input("Length Used (m)", format="%.2f")
    spool_notes = st.text_area("Spool Notes")

    submit_button = st.form_submit_button("🚀 Submit All Entries")

# Save Entries
if submit_button:
    try:
        wound_module_sheet.append_row([
            wound_module_id, module_fk, wind_program_fk, operator_initials, notes_wound,
            mfg_db_wind, mfg_db_potting, mfg_db_mod
        ])
        wrap_per_module_sheet.append_row([
            wrap_per_module_pk, wrap_module_fk, wrap_after_layer, type_of_wrap, wrap_notes
        ])
        spools_per_wind_sheet.append_row([
            spool_per_wind_pk, mfg_db_wind_fk, coated_spool_id, length_used, spool_notes
        ])
        st.success("✅ Data successfully saved in Wound, Wrap, and Spool tables!")
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")
