import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# -------- CONFIG --------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MODULE = "Module Tbl"
TAB_WOUND = "Wound Module Tbl"
TAB_MINI = "Mini Module Tbl"
TAB_PRESSURE_TEST = "Pressure Test Tbl"

# -------- CONNECTION --------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        if not worksheet.get_all_values():
            worksheet.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, prefix):
    records = worksheet.col_values(1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix)]
    return f"{prefix}-{str(max(nums)+1).zfill(3)}" if nums else f"{prefix}-001"

def get_display_label(mid, mtype, wound_df, mini_df):
    if mtype.lower() == "mini":
        label = mini_df[mini_df["Module ID"] == mid]["Module Label"].values
    elif mtype.lower() == "wound":
        label = wound_df[wound_df["Module ID (FK)"] == mid]["Wound Module ID"].values
    else:
        label = []
    return f"{mid} | {mtype} | {label[0] if label.size else '—'}"

# -------- LOAD SHEETS --------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(sheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())
mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())
pressure_test_sheet = get_or_create_tab(sheet, TAB_PRESSURE_TEST, [
    "Pressure Test ID", "Module ID", "Module Type", "Display Label", "Feed Pressure",
    "Permeate Flow", "Pressure Test DateTime", "Operator Initials", "Notes", "Passed"
])

module_df = pd.DataFrame(module_sheet.get_all_records())
module_df["Display"] = module_df.apply(
    lambda row: get_display_label(row["Module ID"], row["Module Type"], wound_df, mini_df),
    axis=1
)
module_options = dict(zip(module_df["Display"], module_df["Module ID"]))

# -------- FORM --------
st.title("🧪 Pressure Test Form (Multi-Measurement)")
st.markdown("Enter multiple pressure & flow readings for a module. Pass/fail and review available.")

with st.form("pressure_test_form", clear_on_submit=True):
    module_display = st.selectbox("Select Module", list(module_options.keys()))
    module_id = module_options[module_display]
    module_type = module_df[module_df["Module ID"] == module_id]["Module Type"].values[0]

    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    passed = st.selectbox("Passed?", ["Yes", "No"])
    test_date = st.date_input("Date", datetime.today())

    st.subheader("➕ Add Multiple Pressure Measurements")
    num = st.number_input("Number of Measurements", min_value=1, value=2, step=1)
    pressures = []
    flows = []

    for i in range(num):
        st.markdown(f"**Measurement {i+1}**")
        pressures.append(st.number_input(f"Feed Pressure {i+1}", key=f"fp_{i}"))
        flows.append(st.number_input(f"Permeate Flow {i+1}", key=f"pf_{i}"))

    submit = st.form_submit_button("💾 Submit All")

# -------- SAVE --------
if submit:
    try:
        for i in range(len(pressures)):
            test_time = datetime.now().time()
            test_dt = datetime.combine(test_date, test_time)
            pt_id = get_last_id(pressure_test_sheet, "PT")
            row = [
                pt_id, module_id, module_type, module_display,
                pressures[i], flows[i], str(test_dt),
                operator_initials, notes, passed
            ]
            pressure_test_sheet.append_row(row)
        st.success("✅ All pressure test entries saved successfully!")
    except Exception as e:
        st.error(f"❌ Error saving entries: {e}")

# -------- LAST 7 DAYS --------
st.subheader("📅 Last 7 Days of Pressure Test Entries")
try:
    df = pd.DataFrame(pressure_test_sheet.get_all_records())
    df["Pressure Test DateTime"] = pd.to_datetime(df["Pressure Test DateTime"], errors="coerce")
    df = df[df["Pressure Test DateTime"] >= datetime.now() - timedelta(days=7)]
    st.dataframe(df if not df.empty else "No records in last 7 days.")
except Exception as e:
    st.error(f"❌ Could not load last 7-day records: {e}")
