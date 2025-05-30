import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd

# ---- CONFIG ----
SHEET_NAME = "R&D Data Form"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), SCOPE)
client = gspread.authorize(CREDS)
spreadsheet = client.open(SHEET_NAME)

def get_or_create_worksheet(sheet, title, headers):
    try:
        ws = sheet.worksheet(title)
        # Fix header if missing or wrong
        if ws.row_values(1) != headers:
            ws.delete_row(1)
            ws.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows="1000", cols="50")
        ws.insert_row(headers, 1)
    return ws

def get_next_id(ws, prefix):
    records = ws.col_values(1)[1:]  # skip header
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix)]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

def filter_7days(records, date_col):
    today = datetime.now().date()
    filtered = []
    for r in records:
        try:
            d = r.get(date_col) or r.get("Date & Time") or r.get("Date")
            # Try parsing both date and datetime
            if d:
                d_obj = datetime.strptime(d, "%Y-%m-%d").date() if len(d) == 10 else datetime.strptime(d, "%Y-%m-%d %H:%M").date()
                if (today - d_obj).days <= 7:
                    filtered.append(r)
        except:
            continue
    return filtered

# ---- Get dropdown data ----
solution_ws = get_or_create_worksheet(spreadsheet, "Solution ID Tbl", ["Solution ID"])
solution_ids = solution_ws.col_values(1)[1:]
pcp_ws = get_or_create_worksheet(spreadsheet, "Pilot Coating Process Tbl", [
    "PCoating ID", "Solution ID", "Date", "Box Temperature", "Box RH", "N2 flow",
    "Load cell slope", "Number of fibers", "Coating Speed", "Tower 1 set point",
    "Tower 1 entry temperature", "Tower 2 set point", "Tower 2 entry temperature",
    "Coating Layer Type (GL/AL/PL)", "Operator Initials", "Ambient Temp", "Ambient %RH", "Notes"])
pcoating_ids = pcp_ws.col_values(1)[1:]
dcp_ws = get_or_create_worksheet(spreadsheet, "Dip Coating Process Tbl", ["DCoating_ID", "Solution ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Date"])
dcoating_ids = dcp_ws.col_values(1)[1:]
ct_ws = get_or_create_worksheet(spreadsheet, "Coater Tension Tbl", [
    "Tension ID", "PCoating ID", "Payout Location", "Tension (g)", "Notes"])
csm_ws = get_or_create_worksheet(spreadsheet, "Coating Solution Mass Tbl", [
    "SolutionMass ID", "Solution ID", "Date & Time", "DCoating ID", "PCoating ID", "Solution Mass", "Operators Initials", "Notes"])

st.title("🧪 Coating Process Form")

tab1, tab2, tab3 = st.tabs(["Pilot Coating", "Coater Tension", "Coating Solution Mass"])

# ------------- PILOT COATING FORM ----------------
with tab1:
    st.header("Pilot Coating Process Entry")
    with st.form("pilot_coating_form", clear_on_submit=True):
        pcoating_id = get_next_id(pcp_ws, "PCOAT")
        st.markdown(f"**Auto-generated PCoating ID:** <span style='color:purple'>{pcoating_id}</span>", unsafe_allow_html=True)
        solution_id = st.selectbox("Solution ID", solution_ids)
        date = st.date_input("Date", datetime.today())
        box_temp = st.number_input("Box Temperature (°C)", min_value=0.0)
        box_rh = st.number_input("Box RH (%)", min_value=0.0)
        n2_flow = st.number_input("N2 flow", min_value=0.0)
        load_cell = st.number_input("Load cell slope", min_value=0.0)
        n_fibers = st.number_input("Number of fibers", min_value=0)
        speed = st.number_input("Coating Speed (m/min)", min_value=0.0)
        t1_sp = st.number_input("Tower 1 set point", min_value=0.0)
        t1_entry = st.number_input("Tower 1 entry temperature", min_value=0.0)
        t2_sp = st.number_input("Tower 2 set point", min_value=0.0)
        t2_entry = st.number_input("Tower 2 entry temperature", min_value=0.0)
        layer = st.selectbox("Coating Layer Type", ["GL", "AL", "PL"])
        operator = st.text_input("Operator Initials")
        amb_temp = st.number_input("Ambient Temp", min_value=0.0)
        amb_rh = st.number_input("Ambient %RH", min_value=0.0)
        notes = st.text_area("Notes")
        submit = st.form_submit_button("Submit Pilot Coating Entry")
        if submit:
            row = [
                pcoating_id, solution_id, date.strftime("%Y-%m-%d"), box_temp, box_rh, n2_flow, load_cell,
                n_fibers, speed, t1_sp, t1_entry, t2_sp, t2_entry, layer, operator, amb_temp, amb_rh, notes
            ]
            pcp_ws.append_row(row)
            st.success(f"✅ Saved with PCoating ID {pcoating_id}")

# ------------- COATER TENSION FORM ----------------
with tab2:
    st.header("Coater Tension Entry (Multi Measurement)")
    with st.form("coater_tension_form", clear_on_submit=True):
        tension_id = get_next_id(ct_ws, "TENS")
        st.markdown(f"**Auto-generated Tension ID:** <span style='color:purple'>{tension_id}</span>", unsafe_allow_html=True)
        pcoating_id = st.selectbox("PCoating ID", pcoating_ids)
        payout = st.selectbox("Payout Location", ["Entry", "Exit", "Other"])
        tension = st.number_input("Tension (g)", min_value=0.0)
        notes = st.text_area("Notes")
        submit = st.form_submit_button("Add Data Point")
        if submit:
            ct_ws.append_row([tension_id, pcoating_id, payout, tension, notes])
            st.success(f"✅ Saved with Tension ID {tension_id}")

# ------------- COATING SOLUTION MASS FORM --------------
with tab3:
    st.header("Coating Solution Mass Entry (Multi)")
    with st.form("solution_mass_form", clear_on_submit=True):
        mass_id = get_next_id(csm_ws, "CMASS")
        st.markdown(f"**Auto-generated SolutionMass ID:** <span style='color:purple'>{mass_id}</span>", unsafe_allow_html=True)
        solution_id = st.selectbox("Solution ID", solution_ids)
        date_time = st.datetime_input("Date & Time", datetime.now())
        dcoating_id = st.selectbox("DCoating ID (optional)", [""] + dcoating_ids)
        pcoating_id = st.selectbox("PCoating ID (optional)", [""] + pcoating_ids)
        mass = st.number_input("Solution Mass", min_value=0.0)
        operator = st.text_input("Operators Initials")
        notes = st.text_area("Notes")
        submit = st.form_submit_button("Add Solution Mass Entry")
        if submit:
            csm_ws.append_row([
                mass_id, solution_id, date_time.strftime("%Y-%m-%d %H:%M"), dcoating_id, pcoating_id, mass, operator, notes
            ])
            st.success(f"✅ Saved with SolutionMass ID {mass_id}")

# ------------ 7-DAY REVIEW (For all tables) -------------
st.markdown("## 📅 7-Day Review")
with st.expander("Pilot Coating Process Tbl (last 7 days)", expanded=False):
    data = pcp_ws.get_all_records()
    st.dataframe(pd.DataFrame(filter_7days(data, "Date")))

with st.expander("Coater Tension Tbl (last 7 days)", expanded=False):
    data = ct_ws.get_all_records()
    st.dataframe(pd.DataFrame(data))  # Tension doesn't have date - adjust as needed

with st.expander("Coating Solution Mass Tbl (last 7 days)", expanded=False):
    data = csm_ws.get_all_records()
    st.dataframe(pd.DataFrame(filter_7days(data, "Date & Time")))
