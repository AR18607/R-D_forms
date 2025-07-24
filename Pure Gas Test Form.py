import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_PURE_GAS = "Pure Gas Test Tbl"
TAB_MODULE = "Module Tbl"
TAB_WOUND = "Wound Module Tbl"
TAB_MINI = "Mini Module Tbl"

# --- Prevent accidental submit on Enter ---
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# --- UTILS ---
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

def compute_permeance(flow_mL_min, area_cm2, feed_psi, perm_psi):
    if feed_psi == perm_psi or area_cm2 == 0:
        return 0
    dp_cmhg = (feed_psi - perm_psi) * 5.174
    flow_mL_s = flow_mL_min / 60
    return flow_mL_s / (area_cm2 * dp_cmhg)

# --- SETUP ---
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
pure_sheet = get_or_create_tab(sheet, TAB_PURE_GAS, [
    "Pure Gas Test ID", "Test Date", "Module ID", "Module Type", "Display Module Label", "Gas",
    "Feed Pressure (psi)", "Perm Pressure (psi)", "Flow (mL/min)", "Operator Initials", "Notes",
    "Permeance", "Selectivity", "Passed (y/n)?"
])

module_df = pd.DataFrame(sheet.worksheet(TAB_MODULE).get_all_records())
wound_df = pd.DataFrame(sheet.worksheet(TAB_WOUND).get_all_records())
mini_df = pd.DataFrame(sheet.worksheet(TAB_MINI).get_all_records())

# --- DISPLAY LABELS ---
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
module_options = dict(zip(module_df["Display"], module_df["Module ID"]))

# --- SESSION STATE FOR READINGS ---
if "readings" not in st.session_state:
    st.session_state.readings = [
        {"Gas": "CO2", "Feed": 0.0, "Perm": 0.0, "Flow": 0.0},
        {"Gas": "N2", "Feed": 0.0, "Perm": 0.0, "Flow": 0.0}
    ]

st.title("🧪 Pure Gas Test Form")
st.markdown("""
You can enter multiple gas readings per module. Selectivity and pass/fail will be computed automatically.<br>
**How Pass/Fail is determined:** At least one CO₂ and one N₂ reading are required to compute selectivity and pass the test.<br>
**Tip:** Use the 'Preview' button to see all calculated values before submitting.
""", unsafe_allow_html=True)

with st.form("pure_gas_test_form", clear_on_submit=False):
    pg_id = get_last_id(pure_sheet, "PGT")
    st.markdown(f"**Pure Gas Test ID:** `{pg_id}`")
    test_date = st.date_input("Test Date", datetime.today())
    module_display = st.selectbox("Select Module", list(module_options.keys()))
    module_id = module_options[module_display]
    module_type = module_display.split("|")[1].strip()
    initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")

    # --- Add/Remove Readings Dynamically ---
    st.subheader("➕ Add Gas Readings")
    n_readings = len(st.session_state.readings)
    for i in range(n_readings):
        st.markdown(f"**Reading {i+1}**")
        col1, col2, col3, col4 = st.columns([2,2,2,2])
        with col1:
            st.session_state.readings[i]["Gas"] = st.selectbox(f"Gas {i+1}", ["CO2", "N2", "O2"], key=f"gas_{i}", index=["CO2", "N2", "O2"].index(st.session_state.readings[i]["Gas"]) if st.session_state.readings[i]["Gas"] in ["CO2", "N2", "O2"] else 0)
        with col2:
            st.session_state.readings[i]["Feed"] = st.number_input(f"Feed Pressure (psi) {i+1}", min_value=0.0, key=f"feed_{i}", value=float(st.session_state.readings[i]["Feed"]))
        with col3:
            st.session_state.readings[i]["Perm"] = st.number_input(f"Perm Pressure (psi) {i+1}", min_value=0.0, key=f"perm_{i}", value=float(st.session_state.readings[i]["Perm"]))
        with col4:
            st.session_state.readings[i]["Flow"] = st.number_input(f"Flow (mL/min) {i+1}", min_value=0.0, key=f"flow_{i}", value=float(st.session_state.readings[i]["Flow"]))
    colA, colB = st.columns([1,1])
    with colA:
        if st.form_submit_button("➕ Add Reading", use_container_width=True):
            st.session_state.readings.append({"Gas": "CO2", "Feed": 0.0, "Perm": 0.0, "Flow": 0.0})
            st.experimental_rerun()
    with colB:
        if n_readings > 2 and st.form_submit_button("➖ Remove Last", use_container_width=True):
            st.session_state.readings.pop()
            st.experimental_rerun()

    area_cm2 = st.number_input("Module Area (cm²)", min_value=0.001, format="%.3f", value=1.000)

    preview = st.form_submit_button("👁️ Preview Calculations")
    submit = st.form_submit_button("💾 Submit", disabled=False)

# --- PREVIEW & SUBMIT LOGIC ---
def calc_results():
    co2_perm, n2_perm = None, None
    rows = []
    for r in st.session_state.readings:
        perm = compute_permeance(r["Flow"], area_cm2, r["Feed"], r["Perm"])
        if r["Gas"] == "CO2":
            co2_perm = perm
        if r["Gas"] == "N2":
            n2_perm = perm
        rows.append({
            "Gas": r["Gas"],
            "Feed Pressure (psi)": r["Feed"],
            "Perm Pressure (psi)": r["Perm"],
            "Flow (mL/min)": r["Flow"],
            "Permeance": round(perm, 6)
        })
    selectivity = round(co2_perm / n2_perm, 6) if co2_perm and n2_perm else 0
    passed = "Yes" if co2_perm and n2_perm else "No"
    return rows, selectivity, passed

if preview or submit:
    calc_rows, selectivity, passed = calc_results()
    st.markdown("### Preview of Results:")
    st.dataframe(pd.DataFrame(calc_rows))
    st.markdown(f"**Selectivity:** `{selectivity}` &nbsp; | &nbsp; **Passed:** `{passed}`")

if submit:
    calc_rows, selectivity, passed = calc_results()
    try:
        # Write each row to the sheet
        for i, r in enumerate(st.session_state.readings):
            permeance = pd.DataFrame(calc_rows).iloc[i]["Permeance"]
            pure_sheet.append_row([
                pg_id, str(test_date), module_id, module_type, module_display, r["Gas"],
                r["Feed"], r["Perm"], r["Flow"], initials, notes, permeance, selectivity, passed
            ])
        st.success(f"✅ Submitted {len(st.session_state.readings)} gas readings with selectivity: `{selectivity}` and Pass: {passed}")
        st.session_state.readings = [
            {"Gas": "CO2", "Feed": 0.0, "Perm": 0.0, "Flow": 0.0},
            {"Gas": "N2", "Feed": 0.0, "Perm": 0.0, "Flow": 0.0}
        ]  # reset for next run
        st.experimental_rerun()
    except Exception as e:
        st.error(f"❌ Failed to save entries: {e}")

# --- LAST 7 DAYS ---
st.subheader("📅 Last 7 Days of Pure Gas Tests")
try:
    pg_df = pd.DataFrame(pure_sheet.get_all_records())
    pg_df["Test Date"] = pd.to_datetime(pg_df["Test Date"], errors="coerce")
    recent = pg_df[pg_df["Test Date"] >= datetime.today() - timedelta(days=7)]
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No entries in the last 7 days.")
except Exception as e:
    st.error(f"❌ Failed to load 7-day data: {e}")
