import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import uuid


# ------------------ CONFIG ------------------

GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_PRESSURE_TEST = "Pressure Test Tbl"

# ------------------ GOOGLE SHEET SETUP ------------------

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

# ------------------ CONNECT ------------------

spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
pressure_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE_TEST,
    ["Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow", "Date", "Time", "Operator Initials", "Notes", "Passed"]
)

# ------------------ UI ------------------

st.title("🧪 Pressure Test Form (Multi-Measurement)")

# Operator and Common Info
module_id = st.text_input("Module ID")
operator = st.text_input("Operator Initials")
notes = st.text_area("Notes")
passed = st.selectbox("Passed?", ["Yes", "No"])
test_date = st.date_input("Date", datetime.today())

# Initialize session state
if "measurements" not in st.session_state:
    st.session_state.measurements = []

# Add Measurement Button
if st.button("➕ Add Measurement"):
    st.session_state.measurements.append({
        "id": str(uuid4()),
        "feed_pressure": 0.0,
        "permeate_flow": 0.0,
        "test_time": datetime.now().time()
    })

# Render each measurement entry
for i, row in enumerate(st.session_state.measurements):
    st.markdown(f"**Measurement #{i+1}**")
    col1, col2, col3 = st.columns(3)
    row["feed_pressure"] = col1.number_input(f"Feed Pressure (psi) #{i+1}", key=f"fp_{i}", value=row["feed_pressure"])
    row["permeate_flow"] = col2.number_input(f"Permeate Flow (L/min) #{i+1}", key=f"pf_{i}", value=row["permeate_flow"])
    row["test_time"] = col3.time_input(f"Time #{i+1}", key=f"time_{i}", value=row["test_time"])
    if st.button(f"❌ Delete Measurement #{i+1}", key=f"del_{i}"):
        st.session_state.measurements.pop(i)
        st.rerun()

# Final Submission
if st.button("✅ Submit All Measurements"):
    for row in st.session_state.measurements:
        pressure_id = f"PT-{str(uuid4())[:8]}"
        pressure_sheet.append_row([
            pressure_id,
            module_id,
            row["feed_pressure"],
            row["permeate_flow"],
            str(test_date),
            row["test_time"].strftime("%H:%M"),
            operator,
            notes,
            passed
        ])
    st.success("✅ All measurements submitted!")
    st.session_state.measurements.clear()


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
