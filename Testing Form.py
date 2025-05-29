import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from uuid import uuid4
from oauth2client.service_account import ServiceAccountCredentials

# --------------- CONFIG ----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MODULE = "Module Tbl"
TAB_PRESSURE = "Pressure Test Tbl"

# --------------- AUTH ----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(sheet, tab_name, headers):
    try:
        worksheet = sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, prefix):
    existing_ids = worksheet.col_values(1)[1:]  # skip header
    nums = [int(r.split("-")[-1]) for r in existing_ids if r.startswith(prefix) and r.split("-")[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

def filter_last_7_days(records, datetime_key):
    today = datetime.now()
    result = []
    for r in records:
        try:
            dt = datetime.strptime(r[datetime_key], "%Y-%m-%d %H:%M:%S")
            if dt >= today - timedelta(days=7):
                result.append(r)
        except:
            continue
    return result

# --------------- CONNECT TO SHEETS ----------------
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
pressure_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE, [
    "Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow", "Date Time",
    "Operator Initials", "Notes", "Passed"
])

module_ids = module_sheet.col_values(1)[1:]  # skip header

# --------------- STREAMLIT UI ----------------
st.title("🧪 Pressure Test Form (Multi-Measurement)")

# Form Section
with st.form("pressure_form", clear_on_submit=True):
    module_id = st.selectbox("Module ID", module_ids)
    operator = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    passed = st.selectbox("Passed?", ["Yes", "No"])
    date_input = st.date_input("Date", datetime.today())
    
    # Handle multiple measurements
    if "measurements" not in st.session_state:
        st.session_state.measurements = []

    st.markdown("### ➕ Add Multiple Pressure Measurements")
    if st.button("➕ Add Measurement"):
        st.session_state.measurements.append({
            "id": str(uuid4()),
            "feed_pressure": 0.0,
            "permeate_flow": 0.0
        })

    for idx, m in enumerate(st.session_state.measurements):
        col1, col2 = st.columns(2)
        m["feed_pressure"] = col1.number_input(f"Feed Pressure (Measurement {idx+1})", min_value=0.0, value=m["feed_pressure"], key=f"feed_{m['id']}")
        m["permeate_flow"] = col2.number_input(f"Permeate Flow (Measurement {idx+1})", min_value=0.0, value=m["permeate_flow"], key=f"perm_{m['id']}")

    submitted = st.form_submit_button("📥 Submit All Measurements")

# Submit Logic
if submitted:
    try:
        for m in st.session_state.measurements:
            pressure_test_id = get_last_id(pressure_sheet, "PT")
            dt_str = datetime.combine(date_input, datetime.now().time()).strftime("%Y-%m-%d %H:%M:%S")
            row = [
                pressure_test_id,
                module_id,
                m["feed_pressure"],
                m["permeate_flow"],
                dt_str,
                operator,
                notes,
                passed
            ]
            pressure_sheet.append_row(row)
        st.success("✅ All pressure test records submitted.")
        st.session_state.measurements = []
    except Exception as e:
        st.error(f"❌ Failed to submit records: {e}")

# --------------- 7-DAY REVIEW ----------------
st.markdown("### 📅 7-Day Review")
try:
    all_records = pressure_sheet.get_all_records()
    filtered = filter_last_7_days(all_records, "Date Time")
    if filtered:
        st.dataframe(pd.DataFrame(filtered))
    else:
        st.info("No entries in the last 7 days.")
except Exception as e:
    st.error(f"❌ Could not load review table: {e}")
