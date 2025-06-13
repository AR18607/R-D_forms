import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# ---------- CONFIG ----------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MODULE = "Module Tbl"
TAB_WOUND = "Wound Module Tbl"
TAB_MINI = "Mini Module Tbl"
TAB_PRESSURE_TEST = "Pressure Test Tbl"

# ---------- UTILS ----------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open(sheet_name)

def get_or_create_tab(sheet, name, headers):
    try:
        tab = sheet.worksheet(name)
        if not tab.get_all_values():
            tab.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        tab = sheet.add_worksheet(title=name, rows="1000", cols="50")
        tab.insert_row(headers, 1)
    return tab

def get_last_id(sheet, prefix):
    ids = sheet.col_values(1)[1:]
    nums = [int(i.split("-")[-1]) for i in ids if i.startswith(prefix)]
    return f"{prefix}-{str(max(nums)+1).zfill(3)}" if nums else f"{prefix}-001"

def filter_last_7_days(df, datetime_col):
    df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')
    return df[df[datetime_col] >= datetime.now() - timedelta(days=7)]

# ---------- INIT ----------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(sheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())
mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())
pressure_sheet = get_or_create_tab(sheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Module Type", "Display Label",
    "Feed Pressure", "Permeate Flow", "Pressure Test DateTime",
    "Operator Initials", "Notes", "Passed"
])

# ---------- MODULE DISPLAY ----------
module_df = pd.DataFrame(module_sheet.get_all_records())

def get_display_label(row):
    mid = row["Module ID"]
    mtype = row["Module Type"].strip().lower()
    if mtype == "mini":
        match = mini_df[mini_df["Module ID"] == mid]
        label = match["Module Label"].values[0] if not match.empty else "—"
    elif mtype == "wound":
        match = wound_df[wound_df["Module ID (FK)"] == mid]
        label = match["Wound Module ID"].values[0] if not match.empty else "—"
    else:
        label = "—"
    return f"{mid} | {mtype.capitalize()} | {label}"

module_df["Display"] = module_df.apply(get_display_label, axis=1)
module_map = dict(zip(module_df["Display"], zip(module_df["Module ID"], module_df["Module Type"])))

# ---------- FORM ----------
st.title("🧪 Pressure Test Form (Multi-Measurement)")
with st.form("pressure_form", clear_on_submit=True):
    module_display = st.selectbox("Module ID", list(module_map.keys()))
    module_id, module_type = module_map[module_display]
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    passed = st.selectbox("Passed?", ["Yes", "No"])
    test_date = st.date_input("Date", value=datetime.today())

    st.markdown("### ➕ Add Multiple Pressure Measurements")
    num_measurements = st.number_input("How many measurements?", min_value=1, value=2, step=1)

    measurements = []
    for i in range(num_measurements):
        st.markdown(f"**Measurement {i+1}**")
        feed = st.number_input(f"Feed Pressure {i+1}", key=f"fp_{i}")
        flow = st.number_input(f"Permeate Flow {i+1}", key=f"pf_{i}")
        measurements.append((feed, flow))

    submitted = st.form_submit_button("💾 Submit")

# ---------- SAVE ----------
if submitted:
    try:
        for feed, flow in measurements:
            pt_id = get_last_id(pressure_sheet, "PT")
            test_time = datetime.now().time()
            test_dt = datetime.combine(test_date, test_time)
            pressure_sheet.append_row([
                pt_id, module_id, module_type, module_display,
                feed, flow, str(test_dt),
                initials, notes, passed
            ])
        st.success("✅ All measurements saved.")
    except Exception as e:
        st.error(f"❌ Error saving measurements: {e}")

# ---------- 7-DAY REVIEW ----------
st.subheader("📅 7-Day Review")
try:
    df = pd.DataFrame(pressure_sheet.get_all_records())
    df = filter_last_7_days(df, "Pressure Test DateTime")
    st.dataframe(df if not df.empty else "No records in the last 7 days.")
except Exception as e:
    st.error(f"❌ Could not load review table: {e}")
