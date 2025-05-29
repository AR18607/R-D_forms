import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import uuid

# ---------------- CONFIGURATION ----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MODULE = "Module Tbl"
TAB_PRESSURE_TEST = "Pressure Test Tbl"

# ---------------- GOOGLE SHEETS FUNCTIONS ----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, prefix):
    ids = worksheet.col_values(1)[1:]
    nums = [int(i.split("-")[-1]) for i in ids if i.startswith(prefix)]
    return f"{prefix}-{str(max(nums)+1 if nums else 1).zfill(3)}"

# ---------------- INIT ----------------
st.set_page_config(page_title="Pressure Test Form", layout="centered")
st.title("🧪 Pressure Test Form")

# ---------------- CONNECT ----------------
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
pressure_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow", "Date Time", "Operator Initials", "Notes", "Passed"
])

module_ids = module_sheet.col_values(1)[1:]

# ---------------- SESSION STATE INIT ----------------
if "measurements" not in st.session_state:
    st.session_state.measurements = []

# ---------------- MULTI-MEASUREMENT UI ----------------
st.subheader("➕ Add Multiple Pressure Measurements")

if st.button("➕ Add Measurement"):
    st.session_state.measurements.append({
        "id": str(uuid.uuid4())[:8],
        "feed_pressure": 0.0,
        "permeate_flow": 0.0
    })

# Common fields
module_id = st.selectbox("Module ID", module_ids)
operator_initials = st.text_input("Operator Initials")
notes = st.text_area("General Notes")
test_date = st.date_input("Pressure Test Date", datetime.now().date())
test_time = st.time_input("Test Time", datetime.now().time())
passed = st.selectbox("Passed?", ["Yes", "No"])

# Show each measurement
for i, m in enumerate(st.session_state.measurements):
    st.markdown(f"**Measurement {i+1}**")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        m["feed_pressure"] = st.number_input(f"Feed Pressure {i+1}", key=f"feed_{i}", step=0.1, value=m["feed_pressure"])
    with col2:
        m["permeate_flow"] = st.number_input(f"Permeate Flow {i+1}", key=f"perm_{i}", step=0.1, value=m["permeate_flow"])
    with col3:
        if st.button("❌ Delete", key=f"del_{i}"):
            st.session_state.measurements.pop(i)
            st.experimental_rerun()

# Submit button
if st.button("🚀 Submit All Measurements"):
    try:
        for m in st.session_state.measurements:
            pt_id = get_last_id(pressure_sheet, "PT")
            dt_str = datetime.combine(test_date, test_time).strftime("%Y-%m-%d %H:%M")
            pressure_sheet.append_row([
                pt_id, module_id, m["feed_pressure"], m["permeate_flow"], dt_str,
                operator_initials, notes, passed
            ])
        st.success("✅ All measurements submitted!")
        st.session_state.measurements = []
    except Exception as e:
        st.error(f"❌ Error submitting data: {e}")

# ---------------- REVIEW TABLE ----------------
st.subheader("📅 7-Day Review")

try:
    records = pressure_sheet.get_all_records()
    df = pd.DataFrame(records)
    df["Date Time"] = pd.to_datetime(df["Date Time"])
    cutoff = datetime.now() - timedelta(days=7)
    recent = df[df["Date Time"] >= cutoff]

    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No records in the last 7 days.")
except Exception as e:
    st.error(f"❌ Could not load review table: {e}")
