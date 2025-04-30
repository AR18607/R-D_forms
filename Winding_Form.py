import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets connection setup
def create_google_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client

# Function to check if a sheet exists and create if not
def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        st.warning(f"⚠️ Worksheet '{tab_name}' already exists. Skipping creation.")
    except gspread.exceptions.WorksheetNotFound:
        try:
            worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
            worksheet.insert_row(headers, 1)
            st.success(f"✅ Created worksheet: '{tab_name}'")
        except gspread.exceptions.APIError as e:
            st.error(f"❌ Failed to create worksheet '{tab_name}': {e}")
            return None
    return worksheet

# Function to get the last ID from the worksheet
def get_last_id(worksheet, prefix):
    try:
        records = worksheet.col_values(1)[1:]  # Skip header
        nums = [int(record.replace(prefix + "-", "")) for record in records if record.startswith(prefix)]
        next_num = max(nums) + 1 if nums else 1
        return f"{prefix}-{next_num:03d}"
    except Exception as e:
        st.error(f"❌ Error fetching last ID: {e}")
        return f"{prefix}-001"

# Create Google Sheet connection
client = create_google_sheet_connection()

# Open spreadsheet
spreadsheet = client.open_by_url("your_spreadsheet_url_here")

# Define tab names and their headers
TAB_WOUND_MODULE = "Wound Module Tbl"
TAB_WRAP_PER_MODULE = "Wrap Per Module Tbl"
TAB_SPOOL_PER_WIND = "Spools Per Wind Tbl"
TAB_WIND_PROGRAM = "Wind Program Tbl"

TAB_HEADERS = {
    TAB_WOUND_MODULE: ["Wound Module ID", "Module ID", "Wind Program ID", "Operator Initials", "Wound Module Notes", "MFG DB Wind ID", "MFG DB Potting ID", "MFG DB Mod ID"],
    TAB_WRAP_PER_MODULE: ["Wrap Per Module PK", "Module ID", "Wrap After Layer #", "Type of Wrap", "Notes"],
    TAB_SPOOL_PER_WIND: ["SpoolPerWind PK", "MFG DB Wind ID", "Coated Spool ID", "Length Used", "Notes"],
    TAB_WIND_PROGRAM: ["Wind Program ID", "Program Name", "Number of Bundles / Wind", "Number of Fibers / Ribbon", "Space Between Ribbons", "Wind Angle (deg)", "Active Fiber Length (inch)", "Total Fiber Length (inch)", "Active Area / Fiber", "Number of Layers", "Number of Loops / Layer", "Active Area / Layer", "Notes"]
}

# Create or fetch the necessary worksheets
wound_module_sheet = get_or_create_tab(spreadsheet, TAB_WOUND_MODULE, TAB_HEADERS[TAB_WOUND_MODULE])
wrap_per_module_sheet = get_or_create_tab(spreadsheet, TAB_WRAP_PER_MODULE, TAB_HEADERS[TAB_WRAP_PER_MODULE])
spool_per_wind_sheet = get_or_create_tab(spreadsheet, TAB_SPOOL_PER_WIND, TAB_HEADERS[TAB_SPOOL_PER_WIND])
wind_program_sheet = get_or_create_tab(spreadsheet, TAB_WIND_PROGRAM, TAB_HEADERS[TAB_WIND_PROGRAM])

# Get the last used IDs for auto-generation
wound_module_id = get_last_id(wound_module_sheet, "WMOD")
wrap_per_module_pk = get_last_id(wrap_per_module_sheet, "WRAP")
spool_per_wind_pk = get_last_id(spool_per_wind_sheet, "SPOOL")
wind_program_id = get_last_id(wind_program_sheet, "WP")

# Streamlit form for Wound Module Entry
with st.form("wound_module_form"):
    st.subheader("🔷 Wound Module Entry")
    wound_module_id_input = st.text_input("Auto-generated Wound Module ID", wound_module_id, disabled=True)
    module_id = st.selectbox("Module ID (from Module Tbl)", ["MOD-001", "MOD-002", "MOD-003"])  # Replace with dynamic fetch
    wind_program_id_input = st.selectbox("Wind Program ID (from Wind Program Tbl)", ["WP-001", "WP-002", "WP-003"])  # Replace with dynamic fetch
    operator_initials = st.text_input("Operator Initials")
    wound_module_notes = st.text_area("Wound Module Notes")
    mfg_db_wind_id = st.text_input("MFG DB Wind ID")
    mfg_db_potting_id = st.text_input("MFG DB Potting ID")
    mfg_db_mod_id = st.number_input("MFG DB Mod ID", min_value=1)

    submit_wound_module = st.form_submit_button("Submit Wound Module Entry")

if submit_wound_module:
    wound_module_data = [
        wound_module_id_input,
        module_id,
        wind_program_id_input,
        operator_initials,
        wound_module_notes,
        mfg_db_wind_id,
        mfg_db_potting_id,
        mfg_db_mod_id
    ]
    # Insert data into Wound Module Tbl (pseudo code - insert data into the sheet)
    st.success(f"✅ Wound Module Entry for {wound_module_id_input} successfully submitted!")

# Form for Wrap Per Module Entry (using similar structure)
with st.form("wrap_per_module_form"):
    st.subheader("🔷 Wrap Per Module Entry")
    wrap_per_module_pk_input = st.text_input("Auto-generated Wrap Per Module PK", wrap_per_module_pk, disabled=True)
    module_id_wrap = st.selectbox("Module ID (Wrap)", ["MOD-001", "MOD-002", "MOD-003"])  # Replace with dynamic fetch
    wrap_after_layer = st.number_input("Wrap After Layer #", min_value=0)
    type_of_wrap = st.selectbox("Type of Wrap", ["Type A", "Type B", "Type C"])
    wrap_notes = st.text_area("Wrap Notes")

    submit_wrap_per_module = st.form_submit_button("Submit Wrap Per Module Entry")

if submit_wrap_per_module:
    wrap_per_module_data = [
        wrap_per_module_pk_input,
        module_id_wrap,
        wrap_after_layer,
        type_of_wrap,
        wrap_notes
    ]
    # Insert data into Wrap Per Module Tbl (pseudo code - insert data into the sheet)
    st.success(f"✅ Wrap Per Module Entry for {wrap_per_module_pk_input} successfully submitted!")

# Form for Spools Per Wind Entry
with st.form("spool_per_wind_form"):
    st.subheader("🔷 Spools Per Wind Entry")
    spool_per_wind_pk_input = st.text_input("Auto-generated Spool Per Wind PK", spool_per_wind_pk, disabled=True)
    mfg_db_wind_id_input = st.text_input("MFG DB Wind ID")
    coated_spool_id = st.text_input("Coated Spool ID")
    length_used = st.number_input("Length Used", min_value=0.0, format="%.2f")
    spool_notes = st.text_area("Spool Notes")

    submit_spool_per_wind = st.form_submit_button("Submit Spools Per Wind Entry")

if submit_spool_per_wind:
    spool_per_wind_data = [
        spool_per_wind_pk_input,
        mfg_db_wind_id_input,
        coated_spool_id,
        length_used,
        spool_notes
    ]
    # Insert data into Spools Per Wind Tbl (pseudo code - insert data into the sheet)
    st.success(f"✅ Spools Per Wind Entry for {spool_per_wind_pk_input} successfully submitted!")

