import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from uuid import uuid4

# ---------------- CONFIGURATION ----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MODULE = "Module Tbl"
TAB_PRESSURE_TEST = "Pressure Test Tbl"

# ---------------- CONNECTION FUNCTIONS ----------------
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
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def filter_last_7_days(df, datetime_col):
    today = datetime.now()
    df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')
    return df[df[datetime_col] >= (today - timedelta(days=7))]

# ---------------- MAIN APP ----------------
st.title("🧪 Pressure Test Form (Multi-Measurement)")

# Connect to Google Sheets
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
pressure_test_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow", "Pressure Test DateTime",
    "Operator Initials", "Notes", "Passed"
])

# Module ID dropdown
existing_module_ids = module_sheet.col_values(1)[1:]
module_id = st.selectbox("Module ID", existing_module_ids)

# Other info (pre-submit)
operator_initials = st.text_input("Operator Initials")
notes = st.text_area("Notes")
passed = st.selectbox("Passed?", ["Yes", "No"])
test_date = st.date_input("Date", value=datetime.today())

# Initialize session state for measurements
if "measurements" not in st.session_state:
    st.session_state.measurements = []

st.markdown("### ➕ Add Multiple Pressure Measurements")
if st.button("➕ Add Measurement"):
    st.session_state.measurements.append({"feed_pressure": 0.0, "permeate_flow": 0.0})

# Input fields for each measurement
for i, m in enumerate(st.session_state.measurements):
    st.markdown(f"**Measurement {i+1}**")
    m["feed_pressure"] = st.number_input(f"Feed Pressure (Measurement {i+1})", key=f"fp_{i}")
    m["permeate_flow"] = st.number_input(f"Permeate Flow (Measurement {i+1})", key=f"pf_{i}")

# Submit all measurements
if st.button("✅ Submit All Measurements"):
    try:
        for m in st.session_state.measurements:
            test_time = datetime.now().time()
            test_datetime = datetime.combine(test_date, test_time)
            pt_id = get_last_id(pressure_test_sheet, "PT")
            pressure_test_sheet.append_row([
                pt_id, module_id, m["feed_pressure"], m["permeate_flow"],
                str(test_datetime), operator_initials, notes, passed
            ])
        st.success("✅ All measurements saved.")
        st.session_state.measurements = []
    except Exception as e:
        st.error(f"❌ Error saving measurements: {e}")

# ---------------- 7-DAY REVIEW ----------------
st.subheader("📅 7-Day Review")
try:
    records = pressure_test_sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        df = filter_last_7_days(df, "Pressure Test DateTime")
        st.dataframe(df if not df.empty else "No records in the last 7 days.")
    else:
        st.info("No data found.")
except Exception as e:
    st.error(f"❌ Could not load review table: {e}")
