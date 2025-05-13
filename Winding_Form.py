import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta

# ----------------- CONFIG -----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
SHEET_KEY = "1uPdUWiiwMdJCYJaxZ5TneFa9h6tbSrs327BVLT5GVPY"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

# Sheet tabs
TAB_MODULE = "Module Tbl"
TAB_WIND_PROGRAM = "Wind Program Tbl"
TAB_WOUND_MODULE = "Wound Module Tbl"
TAB_WRAP_PER_MODULE = "Wrap Per Module Tbl"
TAB_SPOOLS_PER_WIND = "Spools Per Wind Tbl"

# ----------------- CONNECT GOOGLE SHEETS -----------------
def connect_google_sheet(sheet_key):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    
    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_key)
        st.write(f"✅ Successfully connected to: {sheet_key}")
        return sheet
    except gspread.exceptions.APIError as e:
        st.error(f"❌ API Error: {e}")
        return None  # Return None if connection fails

def get_or_create_tab(spreadsheet, tab_name, headers):
    if spreadsheet is None:
        st.error("❌ Failed to connect to Google Sheets.")
        return None
    
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:] if worksheet else []
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    return f"{id_prefix}-{str(max(nums) + 1).zfill(3)}" if nums else f"{id_prefix}-001"

@st.cache_data(ttl=60)  # Cache fetched data for 60 seconds to reduce API calls
def fetch_sheet_data(worksheet):
    try:
        data = worksheet.get_all_values()
        return pd.DataFrame(data[1:], columns=data[0]) if data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error fetching sheet data: {e}")
        return pd.DataFrame()

# ----------------- MAIN APP -----------------
st.title("🌀 Winding Form")

spreadsheet = connect_google_sheet(SHEET_KEY)
if spreadsheet:
    # Create/Connect tabs
    module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
    wind_program_sheet = get_or_create_tab(spreadsheet, TAB_WIND_PROGRAM, [
        "Wind Program ID", "Program Name", "Number of bundles / wind", "Number of fibers / ribbon",
        "Space between ribbons", "Wind Angle (deg)", "Active fiber length (inch)", "Total fiber length (inch)",
        "Active Area / fiber", "Number of layers", "Number of loops / layer", "C - Active area / layer", "Notes", "Date_Time"
    ])
    wound_module_sheet = get_or_create_tab(spreadsheet, TAB_WOUND_MODULE, [
        "Wound Module ID", "Module ID (FK)", "Wind Program ID (FK)", "Operator Initials", "Notes",
        "MFG DB Wind ID", "MFG DB Potting ID", "MFG DB Mod ID", "Date_Time"
    ])
    wrap_per_module_sheet = get_or_create_tab(spreadsheet, TAB_WRAP_PER_MODULE, [
        "WrapPerModule PK", "Module ID (FK)", "Wrap After Layer #", "Type of Wrap", "Notes", "Date_Time"
    ])
    spools_per_wind_sheet = get_or_create_tab(spreadsheet, TAB_SPOOLS_PER_WIND, [
        "SpoolPerWind PK", "MFG DB Wind ID (FK)", "Coated Spool ID", "Length Used", "Notes", "Date_Time"
    ])

    # Fetch Data (Cached)
    wind_data = fetch_sheet_data(wind_program_sheet)
    wound_data = fetch_sheet_data(wound_module_sheet)
    wrap_data = fetch_sheet_data(wrap_per_module_sheet)
    spool_data = fetch_sheet_data(spools_per_wind_sheet)

# ----------------- WIND PROGRAM FORM -----------------
st.subheader("🌬️ Wind Program Entry")
with st.form("wind_program_form"):
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

    wind_submit = st.form_submit_button("➕ Submit Wind Program")
    if wind_submit:
        wind_program_sheet.append_row([
            wind_program_id, program_name, bundles, fibers_per_ribbon, spacing, wind_angle,
            active_length, total_length, active_area, layers, loops_per_layer, area_layer, notes, str(datetime.today())
        ])
        st.success(f"✅ Wind Program {wind_program_id} saved successfully!")

# ----------------- 7-DAYS DATA PREVIEW -----------------
st.subheader("📅 Records (Last 7 Days)")

def filter_last_7_days(df, date_col):
    """Filters DataFrame based on Date column, keeping only last 7 days."""
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    return df[df[date_col] >= datetime.today() - timedelta(days=7)]

try:
    if not wind_data.empty:
        st.subheader("🌬️ Wind Program Table (Last 7 Days)")
        filtered_wind = filter_last_7_days(wind_data, "Date_Time")
        st.write(filtered_wind if not filtered_wind.empty else "No Wind Program records in the last 7 days.")

    if not wound_data.empty:
        st.subheader("🌀 Wound Module Table (Last 7 Days)")
        filtered_wound = filter_last_7_days(wound_data, "Date_Time")
        st.write(filtered_wound if not filtered_wound.empty else "No Wound Module records in the last 7 days.")

    if not wrap_data.empty:
        st.subheader("🛡 Wrap Per Module Table (Last 7 Days)")
        filtered_wrap = filter_last_7_days(wrap_data, "Date_Time")
        st.write(filtered_wrap if not filtered_wrap.empty else "No Wrap records in the last 7 days.")

    if not spool_data.empty:
        st.subheader("🎞 Spools Per Wind Table (Last 7 Days)")
        filtered_spool = filter_last_7_days(spool_data, "Date_Time")
        st.write(filtered_spool if not filtered_spool.empty else "No Spool records in the last 7 days.")

except Exception as e:
    st.error(f"❌ Error loading recent data: {e}")
