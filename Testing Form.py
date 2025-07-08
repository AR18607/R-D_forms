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
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix) and r.split('-')[-1].isdigit()]
    return f"{prefix}-{str(max(nums)+1).zfill(3)}" if nums else f"{prefix}-001"

def get_display_label(mid, mtype, wound_df, mini_df):
    if mtype.lower() == "mini":
        label = mini_df[mini_df["Module ID"] == mid]["Module Label"].values
    elif mtype.lower() == "wound":
        label = wound_df[wound_df["Module ID (FK)"] == mid]["Wound Module ID"].values
    else:
        label = []
    return f"{mid} / {mtype} / {label[0] if label.size else '—'}"

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
if not module_df.empty:
    module_df["Display"] = module_df.apply(
        lambda row: get_display_label(row["Module ID"], row["Module Type"], wound_df, mini_df),
        axis=1
    )
    module_options = dict(zip(module_df["Display"], module_df["Module ID"]))
else:
    module_options = {}

st.title("🧪 Pressure Test Form (Multi-Measurement)")
st.markdown("Enter multiple pressure & flow readings for a module. Pass/fail and review available.")

# --- 1. Select Module, Operator, etc
with st.form("pressure_form_meta", clear_on_submit=False):
    st.markdown("**Select Module**")
    module_display = st.selectbox(
        "Module",
        options=list(module_options.keys()),
        key="module_select",
        help="Type to search by Module ID, Type, or Label"
    )
    module_id = module_options[module_display] if module_display else ""
    module_type = module_df[module_df["Module ID"] == module_id]["Module Type"].values[0] if module_id else ""

    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    test_date = st.date_input("Date", datetime.today())
    submit_meta = st.form_submit_button("Continue to Measurements")

# --- 2. Number of Measurements (Live, outside any form!)
if "num_measurements" not in st.session_state:
    st.session_state["num_measurements"] = 2
if "measures" not in st.session_state:
    st.session_state["measures"] = []

num = st.number_input("Number of Measurements", min_value=1, max_value=20, value=st.session_state["num_measurements"], step=1, key="num_meas_live")

# Sync num_measurements
if num != st.session_state["num_measurements"]:
    st.session_state["num_measurements"] = num
    # Reset measures to proper length
    st.session_state["measures"] = [{"Feed Pressure": 0.0, "Permeate Flow": 0.0} for _ in range(num)]

# Ensure correct length
while len(st.session_state["measures"]) < num:
    st.session_state["measures"].append({"Feed Pressure": 0.0, "Permeate Flow": 0.0})
while len(st.session_state["measures"]) > num:
    st.session_state["measures"].pop()

st.markdown("#### ➕ Enter Measurement Data")
for i in range(num):
    cols = st.columns(2)
    with cols[0]:
        st.session_state["measures"][i]["Feed Pressure"] = st.number_input(
            f"Feed Pressure [{i+1}]", value=st.session_state["measures"][i]["Feed Pressure"], key=f"fp_{i}_live"
        )
    with cols[1]:
        st.session_state["measures"][i]["Permeate Flow"] = st.number_input(
            f"Permeate Flow [{i+1}]", value=st.session_state["measures"][i]["Permeate Flow"], key=f"pf_{i}_live"
        )

df_measure = pd.DataFrame(st.session_state["measures"])
st.markdown("#### 📋 All Entered Measurements")
if not df_measure.empty:
    st.dataframe(df_measure)
    st.line_chart(df_measure, x="Feed Pressure", y="Permeate Flow", use_container_width=True)

# --- Show which PKs will be used
next_pt_id = get_last_id(pressure_test_sheet, "PT")
next_num = int(next_pt_id.split('-')[-1])
pk_list = [f"PT-{str(next_num + i).zfill(3)}" for i in range(num)]
st.info(f"Primary Key(s) that will be used: {', '.join(pk_list)}")

# --- 3. Pass/Fail & Submit
passed = st.selectbox("Passed?", ["Select...", "Yes", "No"], index=0)
if st.button("💾 Submit All (with above Pass/Fail)"):
    if passed == "Select...":
        st.warning("Please select Pass/Fail before submitting.")
    elif not module_id:
        st.warning("Please select a Module.")
    else:
        try:
            for i, row_data in enumerate(st.session_state["measures"]):
                test_time = datetime.now().time()
                test_dt = datetime.combine(test_date, test_time)
                pt_id = pk_list[i]
                row = [
                    pt_id, module_id, module_type, module_display,
                    row_data["Feed Pressure"], row_data["Permeate Flow"], str(test_dt),
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
    if not df.empty and "Pressure Test DateTime" in df.columns:
        df["Pressure Test DateTime"] = pd.to_datetime(df["Pressure Test DateTime"], errors="coerce")
        df_last7 = df[df["Pressure Test DateTime"] >= datetime.now() - timedelta(days=7)]
        if not df_last7.empty:
            st.dataframe(df_last7)
        else:
            st.info("No records in last 7 days.")
    else:
        st.info("No records found yet.")
except Exception as e:
    st.error(f"❌ Could not load last 7-day records: {e}")
