import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# -------- CONFIG --------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_PURE_GAS = "Pure Gas Test Tbl"
TAB_MODULE = "Module Tbl"
TAB_MINI = "Mini Module Tbl"
TAB_WOUND = "Wound Module Tbl"

# -------- UTILS --------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open(sheet_name)

def get_or_create_tab(sheet, name, headers):
    try:
        ws = sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(name, rows="1000", cols="50")
        ws.insert_row(headers, 1)
    return ws

def get_last_id(worksheet, prefix):
    ids = worksheet.col_values(1)[1:]
    nums = [int(i.split('-')[-1]) for i in ids if i.startswith(prefix)]
    return f"{prefix}-{str(max(nums)+1 if nums else 1).zfill(3)}"

def calculate_permeance(flow, area_cm2, dp_psi):
    dp_cmhg = dp_psi * 5.174
    flow_mL_s = flow / 60
    return round(flow_mL_s / area_cm2 / dp_cmhg, 6) if area_cm2 and dp_cmhg else 0

# -------- INIT SHEETS --------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
pure_sheet = get_or_create_tab(sheet, TAB_PURE_GAS, [
    "Pure Gas Test ID", "Test Date", "Module ID", "Module Type", "Wound/Label", "Gas",
    "Feed Pressure (psi)", "Perm Pressure (psi)", "Flow (mL/min)", "Permeance", 
    "Selectivity", "Operator", "Notes", "Passed?"
])
module_df = pd.DataFrame(sheet.worksheet(TAB_MODULE).get_all_records())
mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())
wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())

# -------- BUILD MODULE OPTIONS --------
def module_label(row):
    mtype = row["Module Type"]
    mid = row["Module ID"]
    if mtype.lower() == "mini":
        label = mini_df[mini_df["Module ID"] == mid]["Module Label"].values
        return f"{mid} | Mini | {label[0] if label.size > 0 else '—'}"
    else:
        wid = wound_df[wound_df["Module ID"] == mid]["Wound Module ID"].values
        return f"{mid} | Wound | {wid[0] if wid.size > 0 else '—'}"

module_choices = module_df["Module ID"].tolist()
module_display = {mid: module_label(row) for mid, row in module_df.set_index("Module ID").iterrows()}

# -------- STREAMLIT FORM --------
st.title("🧪 Pure Gas Test Form")
st.markdown("You can enter multiple gas readings per module. Selectivity and pass/fail will be computed automatically.")

with st.form("pure_gas_test_form", clear_on_submit=True):
    pure_id = get_last_id(pure_sheet, "PGT")
    st.markdown(f"**Pure Gas Test ID:** `{pure_id}`")
    test_date = st.date_input("Test Date", value=datetime.today())
    selected_module = st.selectbox("Select Module", module_choices, format_func=lambda x: module_display[x])
    operator = st.text_input("Operator Initials")
    notes = st.text_area("Notes")

    st.subheader("➕ Add Gas Readings")
    num_rows = st.number_input("How many gas readings?", min_value=2, max_value=10, value=2)
    readings = []

    for i in range(int(num_rows)):
        st.markdown(f"**Reading {i+1}**")
        cols = st.columns(4)
        gas = cols[0].selectbox(f"Gas {i+1}", ["CO2", "N2", "O2"], key=f"gas{i}")
        feed = cols[1].number_input(f"Feed Pressure (psi) {i+1}", key=f"feed{i}")
        perm = cols[2].number_input(f"Perm Pressure (psi) {i+1}", key=f"perm{i}")
        flow = cols[3].number_input(f"Flow (mL/min) {i+1}", key=f"flow{i}")
        readings.append((gas, feed, perm, flow))

    area = st.number_input("Module Area (cm²)", min_value=0.01)

    submit = st.form_submit_button("💾 Submit")

# -------- SAVE --------
if submit:
    results = []
    permeance_map = {}

    for gas, feed, perm, flow in readings:
        dp = feed - perm
        perm_val = calculate_permeance(flow, area, dp)
        permeance_map[gas] = perm_val
        results.append([pure_id, str(test_date), selected_module,
                        module_df[module_df["Module ID"] == selected_module]["Module Type"].values[0],
                        module_label(module_df[module_df["Module ID"] == selected_module].iloc[0]),
                        gas, feed, perm, flow, perm_val, "", operator, notes, ""])

    # Compute selectivity if both gases are present
    if "CO2" in permeance_map and "N2" in permeance_map and permeance_map["N2"] > 0:
        selectivity = round(permeance_map["CO2"] / permeance_map["N2"], 4)
        passed = "Yes" if selectivity >= 10 else "No"
    else:
        selectivity = ""
        passed = "No"

    # Fill selectivity and pass/fail in each row
    for row in results:
        row[10] = selectivity
        row[13] = passed

    # Save
    for row in results:
        pure_sheet.append_row(row)

    st.success(f"✅ Submitted {len(results)} gas readings with selectivity: `{selectivity}` and Pass: `{passed}`")

# -------- LAST 7 DAYS --------
st.subheader("📅 Last 7 Days of Pure Gas Tests")
pg_df = pd.DataFrame(pure_sheet.get_all_records())
if not pg_df.empty:
    pg_df["Test Date"] = pd.to_datetime(pg_df["Test Date"], errors="coerce")
    recent = pg_df[pg_df["Test Date"] >= datetime.today() - timedelta(days=7)]
    st.dataframe(recent if not recent.empty else pd.DataFrame([{"Note": "No recent entries."}]))
else:
    st.info("No test entries yet.")
