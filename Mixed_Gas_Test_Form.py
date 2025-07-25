# === IMPORTS ===
import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials


# === CONFIG ===
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MODULE = "Module Tbl"
TAB_WOUND = "Wound Module Tbl"
TAB_MINI = "Mini Module Tbl"
TAB_MIXED = "Mixed Gas Test Tbl"

# Prevent accidental form submit on Enter
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# === UTILS ===
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key = json.loads(st.secrets["gcp_service_account"])
    json_key["private_key"] = json_key["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json_key, scope)
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

def get_display_label(row, wound_df, mini_df):
    mid = row["Module ID"]
    mtype = row["Module Type"].strip().lower()
    if mtype == "mini":
        label = mini_df[mini_df["Module ID"] == mid]["Module Label"].values[0] if not mini_df[mini_df["Module ID"] == mid].empty else "—"
    elif mtype == "wound":
        label = wound_df[wound_df["Module ID (FK)"] == mid]["Wound Module ID"].values[0] if not wound_df[wound_df["Module ID (FK)"] == mid].empty else "—"
    else:
        label = "—"
    return f"{mid} | {mtype.capitalize()} | {label}", mtype, label

# === SHEET SETUP ===
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
mixed_sheet = get_or_create_tab(sheet, TAB_MIXED, [
    "Mixed Gas Test ID", "Mixed Gas Test Date", "Module ID", "Module Type", "Temperature", "Feed Pressure",
    "Retentate Pressure", "Retentate Flow", "Retentate CO2 Comp", "Permeate Pressure",
    "Permeate Flow", "Permeate CO2 Composition", "Permeate O2 Composition", "Ambient Temperature",
    "CO2 Analyzer ID", "Test Rig", "Operator Initials", "Notes", "Passed",
    "C-CO2 Perm", "C - N2 perm", "C - Selectivity", "C - CO2 Flux", "C - stage cut"
])
module_df = pd.DataFrame(sheet.worksheet(TAB_MODULE).get_all_records())
wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())
mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())

# === DISPLAY SETUP ===
module_df["Display"], module_df["Type"], module_df["Label"] = zip(*module_df.apply(lambda row: get_display_label(row, wound_df, mini_df), axis=1))
module_options = dict(zip(module_df["Display"], module_df["Module ID"]))

# === FORM STATE ===
if "previewed" not in st.session_state:
    st.session_state.previewed = False

# === FORM ===
st.title(":test_tube: Mixed Gas Test Form")
with st.form("mixed_form"):
    test_id = get_last_id(mixed_sheet, "MIXG")
    st.markdown(f"**Test ID:** `{test_id}`")
    test_date = st.date_input("Test Date", datetime.today())

    module_display = st.selectbox("Module", list(module_options.keys()))
    module_id = module_options[module_display]
    selected_row = module_df[module_df["Display"] == module_display].iloc[0]
    module_type = selected_row["Type"]
    label = selected_row["Label"]

    st.write(f"**Module Type:** {module_type}")

    temp = st.number_input("Temperature (°C)", format="%.2f")
    feed = st.number_input("Feed Pressure (psi)", format="%.2f")
    r_press = st.number_input("Retentate Pressure (psi)", format="%.2f")
    r_flow = st.number_input("Retentate Flow (L/min)", format="%.2f")
    r_co2 = st.number_input("Retentate CO2 Comp (%)", format="%.2f")
    p_press = st.number_input("Permeate Pressure (psi)", format="%.2f")
    p_flow = st.number_input("Permeate Flow (L/min)", format="%.2f")
    p_co2 = st.number_input("Permeate CO2 Comp (%)", format="%.2f")
    p_o2 = st.number_input("Permeate O2 Comp (%)", format="%.2f")
    amb_temp = st.number_input("Ambient Temperature (°C)", format="%.2f")
    area = st.number_input("Module Area (cm²)", min_value=0.001, format="%.3f")
    analyzer = st.text_input("CO2 Analyzer ID")
    rig = st.selectbox("Test Rig", ["TR-1", "TR-2", "TR-3", "Other"])
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    passed = st.radio("Passed?", ["Yes", "No"])

    preview = st.form_submit_button("🔍 Preview Calculations")
    submit = st.form_submit_button("🚀 Submit Mixed Gas Test")

if preview:
    st.session_state.previewed = True

if st.session_state.previewed:
    if area > 0 and feed > 0 and r_co2 > 0:
        co2_perm = round((p_co2 / 100) * p_flow / area, 6)
        n2_perm = round(((100 - p_co2) / 100) * p_flow / area, 6)
        selectivity = round(co2_perm / n2_perm, 6) if n2_perm != 0 else 0.0
        co2_flux = round(p_flow / area, 6)
        stage_cut = round(p_flow / feed, 6)
    else:
        co2_perm = n2_perm = selectivity = co2_flux = stage_cut = 0.0

    st.markdown("### :bulb: Calculated Values")
    st.write("**C - CO2 Perm:**", co2_perm)
    st.write("**C - N2 Perm:**", n2_perm)
    st.write("**C - Selectivity:**", selectivity)
    st.write("**C - CO2 Flux:**", co2_flux)
    st.write("**C - Stage Cut:**", stage_cut)

if submit and st.session_state.previewed:
    try:
        mixed_sheet.append_row([
            test_id, str(test_date), module_id, module_type, label,
            temp, feed, r_press, r_flow, r_co2, p_press, p_flow,
            p_co2, p_o2, amb_temp, analyzer, rig, initials, notes, passed,
            co2_perm, n2_perm, selectivity, co2_flux, stage_cut
        ])
        st.success(":white_check_mark: Mixed Gas Test record saved successfully!")
        st.session_state.previewed = False
    except Exception as e:
        st.error(f":x: Failed to save: {e}")

st.subheader(":date: Last 7 Days of Mixed Gas Tests")
try:
    df = pd.DataFrame(mixed_sheet.get_all_records())
    df["Mixed Gas Test Date"] = pd.to_datetime(df["Mixed Gas Test Date"], errors="coerce")
    recent = df[df["Mixed Gas Test Date"] >= datetime.today() - timedelta(days=7)]
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No data in the last 7 days.")
except Exception as e:
    st.error(f":x: Could not load recent data: {e}")
