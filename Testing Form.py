import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
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
    nums = []
    for r in records:
        if r.startswith(id_prefix):
            try:
                nums.append(int(r.split('-')[-1]))
            except Exception:
                continue
    if not nums:
        return f"{id_prefix}-001"
    next_num = max(nums) + 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

# ---------------- MAIN APP ----------------

st.title("🧪 Pressure Test Entry (Enhanced)")

# Connect to Google Sheets
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

# Setup Tabs
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
pressure_test_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow", "Pressure Test Date & Time",
    "Operator Initials", "Notes", "Passed"
])

# Fetch Module IDs
existing_module_ids = module_sheet.col_values(1)[1:]  # Skip header

# ---------------- FORM: MULTI-MEASUREMENT ----------------
st.subheader("➕ Add Multiple Pressure Measurements")

if "measurements" not in st.session_state:
    st.session_state.measurements = []

if st.button("➕ Add Measurement"):
    st.session_state.measurements.append({
        "id": str(uuid4()),
        "feed_pressure": 0.0,
        "permeate_flow": 0.0
    })

module_id = st.selectbox("Module ID", existing_module_ids)
operator_initials = st.text_input("Operator Initials")
test_date = st.date_input("Pressure Test Date", datetime.now())
test_time = st.time_input("Pressure Test Time", datetime.now().time())
test_datetime = datetime.combine(test_date, test_time)
notes = st.text_area("Notes")
passed = st.selectbox("Passed?", ["Yes", "No"])

for idx, m in enumerate(st.session_state.measurements):
    st.markdown(f"**Measurement #{idx + 1}**")
    m["feed_pressure"] = st.number_input(f"Feed Pressure {idx+1} (psi)", format="%.2f", key=f"fp_{m['id']}")
    m["permeate_flow"] = st.number_input(f"Permeate Flow {idx+1} (L/min)", format="%.2f", key=f"pf_{m['id']}")

submit_multi = st.button("🚀 Submit All Measurements")

if submit_multi:
    for m in st.session_state.measurements:
        pt_id = get_last_id(pressure_test_sheet, "PT")
        pressure_test_sheet.append_row([
            pt_id, module_id, m["feed_pressure"], m["permeate_flow"],
            str(test_datetime), operator_initials, notes, passed
        ])
    st.success("✅ All measurements saved.")
    st.session_state.measurements = []  # Reset after submission

# ---------------- 7-DAY REVIEW ----------------
st.subheader("📅 Last 7 Days Review")

try:
    records = pressure_test_sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        df["Pressure Test Date & Time"] = pd.to_datetime(df["Pressure Test Date & Time"])
        df_filtered = df[df["Pressure Test Date & Time"] >= datetime.now() - pd.Timedelta(days=7)]
        st.dataframe(df_filtered)
    else:
        st.info("No data found in Pressure Test table.")
except Exception as e:
    st.error(f"❌ Error fetching data: {e}")
