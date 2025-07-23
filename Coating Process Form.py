import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import re

# --------- GOOGLE SHEETS SETUP ---------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
spreadsheet = client.open("R&D Data Form")

def get_or_create_worksheet(sheet, title, headers):
    try:
        worksheet = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=title, rows="1000", cols="50")
        worksheet.append_row(headers)
    return worksheet

# --------- PK GENERATION UTILITIES ---------
def get_next_numeric_id(worksheet, id_column):
    records = worksheet.get_all_records()
    nums = [int(record[id_column]) for record in records if str(record.get(id_column, "")).isdigit()]
    return max(nums) + 1 if nums else 1

def get_next_prefixed_id(worksheet, id_column, prefix):
    records = worksheet.get_all_records()
    nums = []
    for record in records:
        val = str(record.get(id_column, ""))
        m = re.match(rf"^{prefix}-(\d+)$", val)
        if m:
            nums.append(int(m.group(1)))
    next_id = (max(nums) + 1 if nums else 1)
    return f"{prefix}-{next_id:03d}"

# --------- SHEET HEADERS (EXACT) ---------
pcp_headers = [
    "PCoating ID", "Solution ID", "Date", "Box Temperature", "Box RH", "N2 flow", "Load cell slope",
    "Number of fibers", "Coating Speed", "Tower 1 set point", "Tower 1 entry temperature",
    "Tower 2 set point", "Tower 2 entry temperature", "Coating Layer Type (GL/AL/PL)",
    "Operator Initials", "Ambient Temp", "Ambient %RH", "Notes"
]
dcp_headers = [
    "DCoating_ID", "Solution_ID", "Date", "Box_Temperature", "Box_RH", "N2_Flow", "Number_of_Fibers",
    "Coating_Speed", "Annealing_Time", "Annealing_Temperature", "Coating_Layer_Type", "Operator_Initials",
    "Ambient_Temperature", "Ambient_RH", "Notes"
]
ct_headers = ["Tension ID", "PCoating ID", "Payout Location", "Tension (g)", "Notes"]
csm_headers = [
    "SolutionMass ID", "Solution ID", "Date & Time", "DCoating ID", "Pcoating ID",
    "Solution Mass", "Operators Initials", "Notes"
]

# --------- WORKSHEET OBJECTS ---------
pcp_sheet = get_or_create_worksheet(spreadsheet, "Pilot Coating Process Tbl", pcp_headers)
dcp_sheet = get_or_create_worksheet(spreadsheet, "Dip Coating Process Tbl", dcp_headers)
ct_sheet = get_or_create_worksheet(spreadsheet, "Coater Tension Tbl", ct_headers)
csm_sheet = get_or_create_worksheet(spreadsheet, "Coating Solution Mass Tbl", csm_headers)

# --------- REFERENCE SHEETS FOR FK DROPDOWNS ---------
solution_sheet = get_or_create_worksheet(spreadsheet, "Solution ID Tbl", ["Solution ID"])
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ["Batch Fiber ID"])
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", ["UnCoatedSpool ID"])

solution_ids = [record["Solution ID"] for record in solution_sheet.get_all_records() if record.get("Solution ID")]
batch_fiber_ids = [record["Batch Fiber ID"] for record in ufd_sheet.get_all_records() if record.get("Batch Fiber ID")]
uncoated_spool_ids = [record["UnCoatedSpool ID"] for record in usid_sheet.get_all_records() if record.get("UnCoatedSpool ID")]

# --------- UI LAYOUT ---------
st.title("🧪 Coating Process Data Entry")
tabs = st.tabs(["Pilot Coating", "Dip Coating", "Coater Tension", "Solution Mass"])

# --------- PILOT COATING PROCESS FORM ---------
with tabs[0]:
    st.subheader("Pilot Coating Process Entry")
    with st.form("pilot_form"):
        pcoating_id = get_next_prefixed_id(pcp_sheet, "PCoating ID", "PCOAT")
        st.markdown(f"**Auto-generated PCoating ID:** `{pcoating_id}`")
        pilot = {
            "solution_id": st.selectbox("Solution ID", solution_ids, key="p_solution"),
            "date": st.date_input("Date", key="p_date"),
            "box_temp": st.number_input("Box Temperature", min_value=0.0, key="p_box_temp"),
            "box_rh": st.number_input("Box RH", min_value=0.0, key="p_box_rh"),
            "n2_flow": st.number_input("N2 flow", min_value=0.0, key="p_n2"),
            "load_cell_slope": st.number_input("Load cell slope", min_value=0.0, key="p_lcs"),
            "num_fibers": st.number_input("Number of fibers", min_value=0, key="p_fibers"),
            "coating_speed": st.number_input("Coating Speed", min_value=0.0, key="p_speed"),
            "tower1_set": st.number_input("Tower 1 set point", min_value=0.0, key="p_t1sp"),
            "tower1_entry": st.number_input("Tower 1 entry temperature", min_value=0.0, key="p_t1e"),
            "tower2_set": st.number_input("Tower 2 set point", min_value=0.0, key="p_t2sp"),
            "tower2_entry": st.number_input("Tower 2 entry temperature", min_value=0.0, key="p_t2e"),
            "layer_type": st.selectbox("Coating Layer Type (GL/AL/PL)", ["GL", "AL", "PL"], key="p_layer"),
            "operator": st.text_input("Operator Initials", key="p_op"),
            "ambient_temp": st.number_input("Ambient Temp", min_value=0.0, key="p_amb_temp"),
            "ambient_rh": st.number_input("Ambient %RH", min_value=0.0, key="p_amb_rh"),
            "notes": st.text_area("Notes", key="p_notes")
        }
        if st.form_submit_button("Submit Pilot Coating"):
            pcp_sheet.append_row([
                pcoating_id, pilot["solution_id"], pilot["date"].strftime("%Y-%m-%d"),
                pilot["box_temp"], pilot["box_rh"], pilot["n2_flow"], pilot["load_cell_slope"],
                pilot["num_fibers"], pilot["coating_speed"], pilot["tower1_set"],
                pilot["tower1_entry"], pilot["tower2_set"], pilot["tower2_entry"],
                pilot["layer_type"], pilot["operator"], pilot["ambient_temp"],
                pilot["ambient_rh"], pilot["notes"]
            ])
            st.success(f"Saved entry for Pilot Coating ID {pcoating_id}")

# --------- DIP COATING PROCESS FORM ---------
with tabs[1]:
    st.subheader("Dip Coating Process Entry")
    with st.form("dip_form"):
        dcoating_id = get_next_numeric_id(dcp_sheet, "DCoating_ID")
        st.markdown(f"**Auto-generated DCoating ID:** `{dcoating_id}`")
        dip = {
            "solution_id": st.selectbox("Solution_ID", solution_ids, key="d_solution"),
            "date": st.date_input("Date", key="d_date"),
            "box_temp": st.number_input("Box_Temperature", min_value=0.0, key="d_box_temp"),
            "box_rh": st.number_input("Box_RH", min_value=0.0, key="d_box_rh"),
            "n2_flow": st.number_input("N2_Flow", min_value=0.0, key="d_n2"),
            "num_fibers": st.number_input("Number_of_Fibers", min_value=0, key="d_fibers"),
            "coating_speed": st.number_input("Coating_Speed", min_value=0.0, value=1.0, key="d_speed"),  # default value
            "anneal_time": st.number_input("Annealing_Time", min_value=0.0, value=10.0, key="d_anneal_time"),
            "anneal_temp": st.number_input("Annealing_Temperature", min_value=0.0, value=60.0, key="d_anneal_temp"),
            "layer_type": st.selectbox("Coating_Layer_Type", ["GL", "AL", "PL"], key="d_layer"),
            "operator": st.text_input("Operator_Initials", key="d_op"),
            "ambient_temp": st.number_input("Ambient_Temperature", min_value=0.0, key="d_amb_temp"),
            "ambient_rh": st.number_input("Ambient_RH", min_value=0.0, key="d_amb_rh"),
            "notes": st.text_area("Notes", key="d_notes"),
            "batch_fiber": st.selectbox("Batch Fiber ID", batch_fiber_ids, key="d_batch"),
            "spool": st.selectbox("UnCoatedSpool ID", uncoated_spool_ids, key="d_spool"),
        }
        # Order must match your sheet headers!
        if st.form_submit_button("Submit Dip Coating"):
            dcp_sheet.append_row([
                dcoating_id, dip["solution_id"], dip["date"].strftime("%Y-%m-%d"), dip["box_temp"], dip["box_rh"], dip["n2_flow"],
                dip["num_fibers"], dip["coating_speed"], dip["anneal_time"], dip["anneal_temp"],
                dip["layer_type"], dip["operator"], dip["ambient_temp"], dip["ambient_rh"], dip["notes"]
            ])
            st.success(f"Saved entry for Dip Coating ID {dcoating_id}")

# --------- COATER TENSION FORM WITH MULTI-ENTRY ---------
with tabs[2]:
    st.subheader("Coater Tension Entry (Multi Measurement)")
    pcoating_ids = [record["PCoating ID"] for record in pcp_sheet.get_all_records() if record.get("PCoating ID")]
    if "tension_list" not in st.session_state:
        st.session_state.tension_list = []
    with st.form("tension_form"):
        selected_pcoating_id = st.selectbox("PCoating ID", pcoating_ids, key="ct_pcoating")
        payout = st.text_input("Payout Location", key="ct_payout")
        tension_val = st.number_input("Tension (g)", min_value=0.0, key="ct_tension")
        tension_note = st.text_area("Notes", key="ct_note")
        add = st.form_submit_button("Add Tension Measurement")
        if add:
            st.session_state.tension_list.append((selected_pcoating_id, payout, tension_val, tension_note))
    if st.session_state.tension_list:
        st.write("### Preview Entries")
        st.table(pd.DataFrame(st.session_state.tension_list, columns=["PCoating ID", "Payout Location", "Tension (g)", "Notes"]))
    if st.button("Submit All Tension Data"):
        for entry in st.session_state.tension_list:
            tid = get_next_prefixed_id(ct_sheet, "Tension ID", "TENSION")
            ct_sheet.append_row([tid] + list(entry))
        st.session_state.tension_list.clear()
        st.success(":white_check_mark: All entries saved!")

# --------- COATING SOLUTION MASS FORM WITH MULTI-ENTRY ---------
with tabs[3]:
    st.subheader("Coating Solution Mass Entry (Multi Measurement)")
    dcoating_ids = [str(record["DCoating_ID"]) for record in dcp_sheet.get_all_records() if record.get("DCoating_ID")]
    pcoating_ids = [record["PCoating ID"] for record in pcp_sheet.get_all_records() if record.get("PCoating ID")]
    if "mass_list" not in st.session_state:
        st.session_state.mass_list = []
    with st.form("mass_form"):
        sid = st.selectbox("Solution ID", solution_ids, key="sm_solution")
        # Use date and time input widgets
        date_part = st.date_input("Date", key="sm_date")
        time_part = st.time_input("Time", key="sm_time")
        date_time = datetime.combine(date_part, time_part)
        d_id = st.selectbox("DCoating ID (optional)", ["None"] + dcoating_ids, key="sm_dcoating")
        p_id = st.selectbox("Pcoating ID", pcoating_ids, key="sm_pcoating")
        mass = st.number_input("Solution Mass", min_value=0.0, key="sm_mass")
        initials = st.text_input("Operators Initials", key="sm_initials")
        note = st.text_area("Notes", key="sm_note")
        add = st.form_submit_button("Add Solution Mass Measurement")
        if add:
            st.session_state.mass_list.append((
                sid, date_time, d_id if d_id != "None" else "", p_id, mass, initials, note
            ))
    if st.session_state.mass_list:
        st.write("### Preview Mass Entries")
        st.table(pd.DataFrame(
            st.session_state.mass_list,
            columns=["Solution ID", "Date & Time", "DCoating ID", "Pcoating ID", "Solution Mass", "Operators Initials", "Notes"]
        ))
    if st.button("Submit All Mass Entries"):
        for entry in st.session_state.mass_list:
            mid = get_next_numeric_id(csm_sheet, "SolutionMass ID")
            # date_time is a datetime object, format it for storage
            formatted_entry = list(entry)
            formatted_entry[1] = formatted_entry[1].strftime("%Y-%m-%d %H:%M")
            csm_sheet.append_row([mid] + formatted_entry)
        st.session_state.mass_list.clear()
        st.success(":white_check_mark: All mass entries saved!")

# --------- RECENT 7-DAY ENTRIES PREVIEW ---------
def filter_last_7_days(records, date_key):
    today = datetime.today()
    filtered = []
    for record in records:
        date_str = record.get(date_key, "").strip()
        try:
            if " " in date_str:
                date_val = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            else:
                date_val = datetime.strptime(date_str, "%Y-%m-%d")
            if date_val.date() >= (today - timedelta(days=7)).date():
                filtered.append(record)
        except Exception:
            continue
    return filtered

def safe_preview(title, records, key):
    st.markdown(f"### :white_check_mark: {title}")
    filtered = filter_last_7_days(records, key)
    if filtered:
        st.dataframe(pd.DataFrame(filtered))
    else:
        st.write("No entries in the last 7 days.")

st.markdown("## :date: Recent Entries (Last 7 Days)")
safe_preview("Pilot Coating", pcp_sheet.get_all_records(), "Date")
safe_preview("Dip Coating", dcp_sheet.get_all_records(), "Date")
safe_preview("Coater Tension", ct_sheet.get_all_records(), "PCoating ID")
safe_preview("Coating Solution Mass", csm_sheet.get_all_records(), "Date & Time")
