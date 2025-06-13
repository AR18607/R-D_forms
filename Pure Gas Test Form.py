# Paste this inside your Streamlit app script file

import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# ----------------- CONFIG -----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_PURE_GAS_TEST = "Pure Gas Test Tbl"
TAB_MODULE = "Module Tbl"
TAB_WOUND = "Wound Module Tbl"
TAB_MINI = "Mini Module Tbl"

# ----------------- UTILITY FUNCTIONS -----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        ws = spreadsheet.worksheet(tab_name)
        if not ws.get_all_values():
            ws.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        ws.insert_row(headers, 1)
    return ws

def get_last_id(ws, prefix):
    ids = ws.col_values(1)[1:]
    nums = [int(x.split("-")[-1]) for x in ids if x.startswith(prefix)]
    return f"{prefix}-{str(max(nums)+1 if nums else 1).zfill(3)}"

def calculate_permeance(flow_mL_min, area_cm2, dp_cmhg):
    if area_cm2 <= 0 or dp_cmhg <= 0:
        return 0
    flow_mL_s = flow_mL_min / 60
    return flow_mL_s * (1 / area_cm2) * (1 / dp_cmhg)

# ----------------- LOAD SHEETS -----------------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
pure_sheet = get_or_create_tab(sheet, TAB_PURE_GAS_TEST, [
    "Pure Gas Test ID", "Pure Gas Test Date", "Module ID", "Gas",
    "Pressure", "Flow", "Operator Initials", "Notes",
    "C-Permeance", "C-Selectivity", "Passed (y/n)?"
])
module_df = pd.DataFrame(sheet.worksheet(TAB_MODULE).get_all_records())
wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())
mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())

# ----------------- MODULE LABEL MAPPING -----------------
def module_label(row):
    mid = row["Module ID"]
    if row["Module Type"].lower() == "mini":
        label = mini_df[mini_df["Module ID (FK)"] == mid]["Module Label"].values
        return f"{mid} | Mini | {label[0] if len(label) else '—'}"
    else:
        wid = wound_df[wound_df["Module ID (FK)"] == mid]["Wound Module ID"].values
        return f"{mid} | Wound | {wid[0] if len(wid) else '—'}"

module_options = {
    row["Module ID"]: module_label(row)
    for _, row in module_df.iterrows()
}
reverse_module_lookup = {v: k for k, v in module_options.items()}

# ----------------- STREAMLIT UI -----------------
st.title("🧪 Pure Gas Test Form")
with st.form("pure_gas_test_form", clear_on_submit=True):
    test_id = get_last_id(pure_sheet, "PGT")
    st.markdown(f"**Pure Gas Test ID:** `{test_id}`")

    test_date = st.date_input("Pure Gas Test Date", value=datetime.today())
    selected_mod_display = st.selectbox("Select Module", list(module_options.values()))
    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    module_area = st.number_input("Module Area (cm²)", value=0.01, format="%.4f", min_value=0.0001)

    num_readings = st.number_input("Number of Gas Readings", value=2, min_value=1, step=1)
    readings = []
    for i in range(num_readings):
        st.markdown(f"### Gas Reading {i+1}")
        gas = st.selectbox(f"Gas {i+1}", ["CO2", "N2", "O2"], key=f"gas{i}")
        pressure = st.number_input(f"Feed Pressure (psi) {i+1}", key=f"p{i}")
        perm_pressure = st.number_input(f"Perm Pressure (psi) {i+1}", key=f"pp{i}")
        flow = st.number_input(f"Flow (mL/min) {i+1}", key=f"f{i}")
        readings.append((gas, pressure, perm_pressure, flow))

    submit = st.form_submit_button("Submit")

# ----------------- SAVE LOGIC -----------------
if submit:
    gas_results = []
    co2_perm, n2_perm = None, None

    for gas, p1, p2, f in readings:
        dp = (p1 - p2) * 5.174  # psi → cmHg
        permeance = round(calculate_permeance(f, module_area, dp), 4)
        gas_results.append((gas, p1, f, permeance))
        if gas == "CO2":
            co2_perm = permeance
        elif gas == "N2":
            n2_perm = permeance

    selectivity = round(co2_perm / n2_perm, 4) if co2_perm and n2_perm else 0
    passed = "Yes" if selectivity >= 20 else "No"

    mod_id = reverse_module_lookup[selected_mod_display]
    for gas, p, f, perm in gas_results:
        pure_sheet.append_row([
            test_id, str(test_date), mod_id, gas,
            p, f, operator_initials, notes,
            perm,
            selectivity if gas == "CO2" else "",
            passed if gas == "CO2" else ""
        ])
    st.success(f"✅ Submitted {len(gas_results)} readings. Selectivity: `{selectivity}`. Passed: {passed}")

# ----------------- LAST 7 DAYS -----------------
st.markdown("### 📅 Last 7 Days of Pure Gas Tests")
try:
    df = pd.DataFrame(pure_sheet.get_all_records())
    df["Pure Gas Test Date"] = pd.to_datetime(df["Pure Gas Test Date"], errors="coerce")
    recent_df = df[df["Pure Gas Test Date"] >= datetime.today() - timedelta(days=7)]
    st.dataframe(recent_df)
except Exception as e:
    st.error(f"Error loading table: {e}")
