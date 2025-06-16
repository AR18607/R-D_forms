import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
import json

# ---------- CONFIG ----------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MIXED_GAS = "Mixed Gas Test Tbl"
TAB_MODULE = "Module Tbl"
TAB_MINI = "Mini Module Tbl"
TAB_WOUND = "Wound Module Tbl"

# ---------- CONNECTION SETUP ----------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key = json.loads(st.secrets["gcp_service_account"])
    json_key["private_key"] = json_key["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json_key, scope)
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

# ---------- DISPLAY FORMAT ----------
def get_display_label(row, mini_df, wound_df):
    mid = row["Module ID"]
    mtype = row["Module Type"].strip().lower()
    if mtype == "mini":
        label = mini_df.loc[mini_df["Module ID"] == mid, "Module Label"].values[0] if mid in mini_df["Module ID"].values else "—"
    elif mtype == "wound":
        label = wound_df.loc[wound_df["Module ID (FK)"] == mid, "Wound Module ID"].values[0] if mid in wound_df["Module ID (FK)"].values else "—"
    else:
        label = "—"
    return f"{mid} | {mtype.capitalize()} | {label}"

# ---------- SHEET LOAD ----------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
mixed_sheet = get_or_create_tab(sheet, TAB_MIXED_GAS, [
    "Mixed Gas Test ID", "Test Date", "Module ID", "Module Type", "Display Label",
    "Temperature", "Feed Pressure", "Retentate Pressure", "Retentate Flow", "Retentate CO2 Comp",
    "Permeate Pressure", "Permeate Flow", "Permeate CO2 Comp", "Permeate O2 Comp", "Ambient Temp",
    "CO2 Analyzer ID", "Test Rig", "Operator Initials", "Notes", "Passed",
    "C - Selectivity", "C - CO2 Flux", "C - Stage Cut"
])

module_df = pd.DataFrame(sheet.worksheet(TAB_MODULE).get_all_records())
mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())
wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())
module_df["Display"] = module_df.apply(lambda row: get_display_label(row, mini_df, wound_df), axis=1)
module_map = dict(zip(module_df["Display"], module_df["Module ID"]))

# ---------- FORM ----------
st.title("🧪 Mixed Gas Test Form")
st.markdown("You can view calculated values before submission.")
with st.form("mixed_gas_test_form", clear_on_submit=True):
    test_id = get_last_id(mixed_sheet, "MIXG")
    st.markdown(f"**Mixed Gas Test ID:** `{test_id}`")

    test_date = st.date_input("Test Date", datetime.today())
    selected_display = st.selectbox("Select Module", list(module_map.keys()))
    module_id = module_map[selected_display]
    module_type = selected_display.split("|")[1].strip()

    temp = st.number_input("Temperature (°C)", format="%.2f")
    feed_pressure = st.number_input("Feed Pressure (psi)", format="%.2f")
    ret_pressure = st.number_input("Retentate Pressure (psi)", format="%.2f")
    ret_flow = st.number_input("Retentate Flow (L/min)", format="%.2f")
    ret_co2 = st.number_input("Retentate CO2 Comp (%)", format="%.2f")
    perm_pressure = st.number_input("Permeate Pressure (psi)", format="%.2f")
    perm_flow = st.number_input("Permeate Flow (L/min)", format="%.2f")
    perm_co2 = st.number_input("Permeate CO2 Comp (%)", format="%.2f")
    perm_o2 = st.number_input("Permeate O2 Comp (%)", format="%.2f")
    amb_temp = st.number_input("Ambient Temperature (°C)", format="%.2f")
    analyzer = st.text_input("CO2 Analyzer ID")
    test_rig = st.selectbox("Test Rig", ["TR-1", "TR-2", "TR-3", "Other"])
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    passed = st.radio("Passed?", ["Yes", "No"])
    area = st.number_input("Module Area (cm²)", min_value=0.001, format="%.3f")

    # --- Calculated values ---
    selectivity = round(perm_co2 / ret_co2, 3) if ret_co2 else 0
    flux = round(perm_flow / area, 6) if area else 0
    stage_cut = round(perm_flow / feed_pressure, 3) if feed_pressure else 0

    st.markdown("### 💡 Calculated Values (before submission)")
    st.markdown(f"**C - Selectivity:** `{selectivity}`")
    st.markdown(f"**C - CO2 Flux:** `{flux}`")
    st.markdown(f"**C - Stage Cut:** `{stage_cut}`")

    submit = st.form_submit_button("🚀 Submit Mixed Gas Test")

# ---------- SAVE ----------
if submit:
    try:
        mixed_sheet.append_row([
            test_id, str(test_date), module_id, module_type, selected_display,
            temp, feed_pressure, ret_pressure, ret_flow, ret_co2,
            perm_pressure, perm_flow, perm_co2, perm_o2, amb_temp,
            analyzer, test_rig, initials, notes, passed,
            selectivity, flux, stage_cut
        ])
        st.success("✅ Mixed Gas Test record saved successfully!")
    except Exception as e:
        st.error(f"❌ Failed to save data: {e}")

# ---------- LAST 7 DAYS ----------
st.subheader("📅 Last 7 Days of Mixed Gas Tests")
try:
    df = pd.DataFrame(mixed_sheet.get_all_records())
    df["Test Date"] = pd.to_datetime(df["Test Date"], errors="coerce")
    recent = df[df["Test Date"] >= datetime.today() - timedelta(days=7)]
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No records in last 7 days.")
except Exception as e:
    st.error(f"❌ Could not load recent data: {e}")
