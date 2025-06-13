import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- CONFIG ---
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MIXED_GAS = "Mixed Gas Test Tbl"
TAB_MODULE = "Module Tbl"
TAB_WOUND = "Wound Module Tbl"
TAB_MINI = "Mini Module Tbl"

# --- AUTH ---
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
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

# --- DISPLAY HELPERS ---
def get_display_label(row):
    mid = row["Module ID"]
    mtype = row["Module Type"].strip().lower()
    label = "—"
    if mtype == "mini":
        match = mini_df[mini_df["Module ID"] == mid]
        label = match["Module Label"].values[0] if not match.empty else "—"
    elif mtype == "wound":
        match = wound_df[wound_df["Module ID (FK)"] == mid]
        label = match["Wound Module ID"].values[0] if not match.empty else "—"
    return f"{mid} | {mtype.capitalize()} | {label}"

# --- STARTUP ---
try:
    sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
    module_df = pd.DataFrame(sheet.worksheet(TAB_MODULE).get_all_records())
    mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())
    wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())
    mixed_gas_sheet = get_or_create_tab(sheet, TAB_MIXED_GAS, [
        "Mixed Gas Test ID", "Mixed Gas Test Date", "Module ID", "Module Type", "Display Label", 
        "Temperature", "Feed Pressure", "Retentate Pressure", "Retentate Flow", "Retentate CO2 Comp",
        "Permeate Pressure", "Permeate Flow", "Permeate CO2 Composition", "Permeate O2 Composition",
        "Ambient Temperature", "CO2 Analyzer ID", "Test Rig", "Operator Initials", "Notes", "Passed",
        "C - Selectivity", "C - CO2 Flux", "C - Stage Cut"
    ])
    module_df["Display"] = module_df.apply(get_display_label, axis=1)
    module_options = dict(zip(module_df["Display"], module_df["Module ID"]))
except Exception:
    st.stop()

# --- UI ---
st.title("🧪 Mixed Gas Test Form")
st.markdown("Select a module and enter test values. Calculated results appear before submission.")
st.markdown("<style>button[title='Submit'] {margin-top: 20px !important;} form button {display: none;}</style>", unsafe_allow_html=True)

with st.form("mixed_gas_form", clear_on_submit=True):
    mix_id = get_last_id(mixed_gas_sheet, "MIXG")
    st.markdown(f"**Mixed Gas Test ID:** `{mix_id}`")
    test_date = st.date_input("Test Date", value=datetime.today())
    module_display = st.selectbox("Select Module", list(module_options.keys()))
    module_id = module_options[module_display]
    module_type = module_display.split("|")[1].strip()

    temp = st.number_input("Temperature (°C)")
    feed_p = st.number_input("Feed Pressure (psi)")
    ret_p = st.number_input("Retentate Pressure (psi)")
    ret_flow = st.number_input("Retentate Flow (L/min)")
    ret_co2 = st.number_input("Retentate CO2 Composition (%)")
    perm_p = st.number_input("Permeate Pressure (psi)")
    perm_flow = st.number_input("Permeate Flow (L/min)")
    perm_co2 = st.number_input("Permeate CO2 Composition (%)")
    perm_o2 = st.number_input("Permeate O2 Composition (%)")
    amb_temp = st.number_input("Ambient Temperature (°C)")
    analyzer_id = st.text_input("CO2 Analyzer ID")
    rig = st.selectbox("Test Rig", ["TR-1", "TR-2", "TR-3", "Other"])
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    passed = st.radio("Passed?", ["Yes", "No"])

    # AREA for calculation (ask user for module area)
    area = st.number_input("Module Area (cm²)", min_value=0.001, format="%.3f")

    # CALCULATIONS
    selectivity = round(perm_co2 / (100 - perm_co2), 3) if perm_co2 < 100 else 0
    co2_flux = round(perm_flow / area, 3) if area else 0
    stage_cut = round(perm_flow / feed_p, 3) if feed_p else 0

    st.markdown("### 💡 Calculated Values (before submission)")
    st.write(f"**C - Selectivity:** `{selectivity}`")
    st.write(f"**C - CO2 Flux:** `{co2_flux}`")
    st.write(f"**C - Stage Cut:** `{stage_cut}`")

    submitted = st.form_submit_button("🚀 Submit Mixed Gas Test")

# --- SUBMIT ---
if submitted:
    try:
        mixed_gas_sheet.append_row([
            mix_id, str(test_date), module_id, module_type, module_display, temp,
            feed_p, ret_p, ret_flow, ret_co2, perm_p, perm_flow, perm_co2, perm_o2,
            amb_temp, analyzer_id, rig, initials, notes, passed,
            selectivity, co2_flux, stage_cut
        ])
        st.success("✅ Mixed Gas Test record saved successfully!")
    except Exception as e:
        st.error(f"❌ Failed to save data: {e}")

# --- LAST 7 DAYS ---
st.subheader("📅 Last 7 Days of Mixed Gas Tests")
try:
    df = pd.DataFrame(mixed_gas_sheet.get_all_records())
    df["Mixed Gas Test Date"] = pd.to_datetime(df["Mixed Gas Test Date"], errors='coerce')
    recent = df[df["Mixed Gas Test Date"] >= datetime.today() - timedelta(days=7)]
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No tests in the last 7 days.")
except Exception as e:
    st.warning("⚠️ Could not load previous records. Try again later.")
