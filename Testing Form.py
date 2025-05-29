# ------------------ PRESSURE TEST FORM (Multi-Measurement) ------------------
# 📅 Season 2 Update – May 2025

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

# ---------------- CONNECTIONS ----------------
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

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]
    nums = []
    for r in records:
        if r.startswith(id_prefix):
            try:
                nums.append(int(r.split('-')[-1]))
            except:
                continue
    next_num = max(nums)+1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def filter_last_7_days(df, date_col):
    today = datetime.today().date()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    return df[df[date_col].dt.date >= today - timedelta(days=7)]

# ---------------- SHEET SETUP ----------------
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(spreadsheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
pressure_sheet = get_or_create_tab(spreadsheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Feed Pressure", "Permeate Flow",
    "Date", "Time", "Operator Initials", "Notes", "Passed"
])

module_ids = module_sheet.col_values(1)[1:]

# ---------------- FORM UI ----------------
st.title("🧪 Pressure Test Form (Multi-Measurement)")

# Generate Pressure Test ID
pressure_test_id = get_last_id(pressure_sheet, "PT")
st.markdown(f"### Auto-generated Test ID: `{pressure_test_id}`")

module_id = st.selectbox("Module ID", module_ids)
operator = st.text_input("Operator Initials")
notes = st.text_area("Notes")
passed = st.selectbox("Passed?", ["Yes", "No"])
test_date = st.date_input("Date", value=datetime.today())

# Initialize measurements list
if "measurements" not in st.session_state:
    st.session_state.measurements = []

st.markdown("### ➕ Add Multiple Measurements")

if st.button("➕ Add Measurement"):
    st.session_state.measurements.append({"feed": 0.0, "perm": 0.0, "time": datetime.now().time()})

# Show dynamic measurement input fields
for idx, entry in enumerate(st.session_state.measurements):
    col1, col2, col3 = st.columns(3)
    with col1:
        entry["feed"] = st.number_input(f"Feed Pressure {idx+1}", value=entry["feed"], key=f"feed_{idx}")
    with col2:
        entry["perm"] = st.number_input(f"Permeate Flow {idx+1}", value=entry["perm"], key=f"perm_{idx}")
    with col3:
        entry["time"] = st.time_input(f"Time {idx+1}", value=entry["time"], key=f"time_{idx}")

# Submit all measurements
if st.button("✅ Submit All Measurements"):
    try:
        for m in st.session_state.measurements:
            pressure_sheet.append_row([
                get_last_id(pressure_sheet, "PT"),
                module_id,
                m["feed"],
                m["perm"],
                test_date.strftime("%Y-%m-%d"),
                m["time"].strftime("%H:%M:%S"),
                operator,
                notes,
                passed
            ])
        st.success("✅ All measurements submitted.")
        st.session_state.measurements = []
    except Exception as e:
        st.error(f"❌ Failed to submit measurements: {e}")

# ---------------- 7-DAY REVIEW ----------------
st.subheader("📅 7-Day Review")

try:
    df = pd.DataFrame(pressure_sheet.get_all_records())
    if not df.empty:
        if "Date" in df.columns:
            recent_df = filter_last_7_days(df, "Date")
            if not recent_df.empty:
                st.dataframe(recent_df)
            else:
                st.info("No records in last 7 days.")
        else:
            st.warning("⚠️ 'Date' column not found in sheet.")
    else:
        st.info("No pressure test records found.")
except Exception as e:
    st.error(f"❌ Could not load review table: {e}")
