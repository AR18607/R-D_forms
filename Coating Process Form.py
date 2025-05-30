# ----------------- COATING PROCESS FORM WITH UPDATES -----------------
# 📅 Season 2 Update – May 2025
# ✅ Supports: Tabbed Layout, Add Measurement for Tension, Optional DCoatingID, Time Field, and Add Solution Mass Button

import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime,timedelta
import pandas as pd

# ----------------- GOOGLE SHEETS SETUP -----------------
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

def get_next_id(worksheet, id_column):
    records = worksheet.get_all_records()
    if records:
        last_id = max([int(record[id_column]) for record in records if str(record[id_column]).isdigit()])
        return last_id + 1
    else:
        return 1

# ----------------- DATA LOADING -----------------
solution_sheet = get_or_create_worksheet(spreadsheet, "Solution ID Tbl", ["Solution ID"])
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ["Batch_Fiber_ID"])
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", ["UncoatedSpool_ID"])

solution_ids = [record["Solution ID"] for record in solution_sheet.get_all_records()]
batch_fiber_ids = [record["Batch_Fiber_ID"] for record in ufd_sheet.get_all_records()]
uncoated_spool_ids = [record["UncoatedSpool_ID"] for record in usid_sheet.get_all_records()]

# ----------------- WORKSHEETS SETUP -----------------
pcp_sheet = get_or_create_worksheet(spreadsheet, "Pilot Coating Process Tbl", [
    "PCoating_ID", "Solution ID", "Date", "Box_Temperature", "Box_RH", "N2_Flow",
    "Load_Cell_Slope", "Number_of_Fibers", "Coating_Speed", "Tower_1_Set_Point",
    "Tower_1_Entry_Temperature", "Tower_2_Set_Point", "Tower_2_Entry_Temperature",
    "Coating_Layer_Type", "Operator_Initials", "Ambient_Temperature", "Ambient_RH", "Notes"])

dcp_sheet = get_or_create_worksheet(spreadsheet, "Dip Coating Process Tbl", [
    "DCoating_ID", "Solution ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Date", "Box_Temperature",
    "Box_RH", "N2_Flow", "Number_of_Fibers", "Coating_Speed", "Annealing_Time",
    "Annealing_Temperature", "Coating_Layer_Type", "Operator_Initials", "Ambient_Temperature",
    "Ambient_RH", "Notes"])

ct_sheet = get_or_create_worksheet(spreadsheet, "Coater Tension Tbl", [
    "Tension_ID", "PCoating_ID", "Payout_Location", "Tension", "Notes"])

csm_sheet = get_or_create_worksheet(spreadsheet, "Coating Solution Mass Tbl", [
    "SolutionMass_ID", "Solution ID", "Date_Time", "DCoating_ID", "PCoating_ID",
    "Solution_Mass", "Operators_Initials", "Notes"])

# ----------------- STREAMLIT LAYOUT -----------------
st.title("🧪 Coating Process Entry")
tabs = st.tabs(["Pilot Coating", "Dip Coating", "Coater Tension", "Solution Mass"])

# ----------------- PILOT COATING FORM -----------------
with tabs[0]:
    st.subheader("Pilot Coating Process Entry")
    with st.form("pilot_form"):
        pcoating_id = get_next_id(pcp_sheet, "PCoating_ID")
        st.markdown(f"**Auto-generated ID:** `{pcoating_id}`")
        fields = {
            "selected_solution_id": st.selectbox("Solution ID", solution_ids),
            "date": st.date_input("Date"),
            "box_temperature": st.number_input("Box Temperature (°C)", min_value=0.0),
            "box_rh": st.number_input("Box RH (%)", min_value=0.0),
            "n2_flow": st.number_input("N2 Flow (L/min)", min_value=0.0),
            "load_cell_slope": st.number_input("Load Cell Slope", min_value=0.0),
            "number_of_fibers": st.number_input("Number of Fibers", min_value=0),
            "coating_speed": st.number_input("Coating Speed (m/min)", min_value=0.0),
            "tower1_set_point": st.number_input("Tower 1 Set Point (°C)", min_value=0.0),
            "tower1_entry_temp": st.number_input("Tower 1 Entry Temp (°C)", min_value=0.0),
            "tower2_set_point": st.number_input("Tower 2 Set Point (°C)", min_value=0.0),
            "tower2_entry_temp": st.number_input("Tower 2 Entry Temp (°C)", min_value=0.0),
            "coating_layer_type": st.selectbox("Layer Type", ["GL", "AL", "PL"]),
            "operator_initials": st.text_input("Operator Initials"),
            "ambient_temp": st.number_input("Ambient Temp (°C)", min_value=0.0),
            "ambient_rh": st.number_input("Ambient RH (%)", min_value=0.0),
            "notes": st.text_area("Notes")
        }
        if st.form_submit_button("Submit Pilot Coating"):
            pcp_sheet.append_row([pcoating_id, fields["selected_solution_id"], fields["date"].strftime("%Y-%m-%d")] +
                [fields[k] for k in list(fields.keys())[2:]])
            st.success(f"✅ Entry saved with ID {pcoating_id}")

# ----------------- DIP COATING FORM -----------------
with tabs[1]:
    st.subheader("Dip Coating Process Entry")
    with st.form("dip_form"):
        dcoating_id = get_next_id(dcp_sheet, "DCoating_ID")
        st.markdown(f"**Auto-generated ID:** `{dcoating_id}`")
        dip = {
            "solution": st.selectbox("Solution ID", solution_ids),
            "batch": st.selectbox("Batch Fiber ID", batch_fiber_ids),
            "spool": st.selectbox("Uncoated Spool ID", uncoated_spool_ids),
            "date": st.date_input("Date"),
            "box_temp": st.number_input("Box Temp (°C)", min_value=0.0),
            "rh": st.number_input("RH (%)", min_value=0.0),
            "n2": st.number_input("N2 Flow", min_value=0.0),
            "fibers": st.number_input("# Fibers", min_value=0),
            "speed": st.number_input("Speed", min_value=0.0),
            "anneal_time": st.number_input("Annealing Time", min_value=0.0),
            "anneal_temp": st.number_input("Annealing Temp", min_value=0.0),
            "layer": st.selectbox("Layer", ["GL", "AL", "PL"]),
            "op": st.text_input("Initials"),
            "amb_temp": st.number_input("Ambient Temp", min_value=0.0),
            "amb_rh": st.number_input("Ambient RH", min_value=0.0),
            "note": st.text_area("Notes")
        }
        if st.form_submit_button("Submit Dip Coating"):
            dcp_sheet.append_row([dcoating_id, dip["solution"], dip["batch"], dip["spool"], dip["date"].strftime("%Y-%m-%d")] +
                                 [dip[k] for k in list(dip.keys())[4:]])
            st.success(f"✅ Entry saved with ID {dcoating_id}")

# ----------------- COATER TENSION FORM WITH MULTI-ENTRY -----------------
with tabs[2]:
    st.subheader("Coater Tension Entry (Multi Measurement)")
    pcoating_ids = [record["PCoating_ID"] for record in pcp_sheet.get_all_records()]
    tension_data = []
    selected_pcoating_id = st.selectbox("PCoating ID", pcoating_ids)

    if "tension_list" not in st.session_state:
        st.session_state.tension_list = []

    with st.form("tension_form"):
        payout = st.text_input("Payout Location")
        tension_val = st.number_input("Tension (g)", min_value=0.0)
        tension_note = st.text_area("Notes")
        add = st.form_submit_button("Add Data Point")
        if add:
            st.session_state.tension_list.append((payout, tension_val, tension_note))

    if st.session_state.tension_list:
        st.write("### Preview Entries")
        st.table(pd.DataFrame(st.session_state.tension_list, columns=["Payout", "Tension", "Notes"]))

    if st.button("Submit All Tension Data"):
        for payout, tension_val, note in st.session_state.tension_list:
            tid = get_next_id(ct_sheet, "Tension_ID")
            ct_sheet.append_row([tid, selected_pcoating_id, payout, tension_val, note])
        st.session_state.tension_list.clear()
        st.success("✅ All entries saved!")

# ----------------- COATING SOLUTION MASS ENTRY WITH MULTI-ENTRY -----------------
with tabs[3]:
    st.subheader("Coating Solution Mass Entry (Multi)")
    dcoating_ids = [record["DCoating_ID"] for record in dcp_sheet.get_all_records()]
    pcoating_ids = [record["PCoating_ID"] for record in pcp_sheet.get_all_records()]

    if "mass_list" not in st.session_state:
        st.session_state.mass_list = []

    with st.form("mass_form"):
        sid = st.selectbox("Solution ID", solution_ids)
        date_time = st.datetime_input("Date & Time")
        d_id = st.selectbox("DCoating ID (optional)", ["None"] + dcoating_ids)
        p_id = st.selectbox("PCoating ID", pcoating_ids)
        mass = st.number_input("Mass (g)", min_value=0.0)
        initials = st.text_input("Operator Initials")
        note = st.text_area("Notes")
        add = st.form_submit_button("Add Solution Mass")
        if add:
            st.session_state.mass_list.append((sid, date_time, d_id if d_id != "None" else "", p_id, mass, initials, note))

    if st.session_state.mass_list:
        st.write("### Preview Mass Entries")
        st.dataframe(pd.DataFrame(st.session_state.mass_list, columns=["Solution ID", "Date_Time", "DCoating ID", "PCoating ID", "Mass", "Initials", "Notes"]))

    if st.button("Submit All Mass Entries"):
        for sid, dt, d_id, p_id, mass, initials, note in st.session_state.mass_list:
            mid = get_next_id(csm_sheet, "SolutionMass_ID")
            csm_sheet.append_row([mid, sid, dt.strftime("%Y-%m-%d %H:%M"), d_id, p_id, mass, initials, note])
        st.session_state.mass_list.clear()
        st.success("✅ All mass entries saved!")

def filter_last_7_days(records, date_key):
    today = datetime.today()
    filtered = []
    for record in records:
        date_str = record.get(date_key, "").strip()
        try:
            date_val = datetime.strptime(date_str, "%Y-%m-%d")
            if date_val.date() >= (today - timedelta(days=7)).date():
                filtered.append(record)
        except:
            continue
    return filtered

# ----------------- LAST 7 DAYS PREVIEW -----------------
st.markdown("## 📅 Recent Entries (Last 7 Days)")

def safe_preview(title, records, key):
    st.markdown(f"### ✅ {title}")
    filtered = filter_last_7_days(records, key)
    if filtered:
        st.dataframe(pd.DataFrame(filtered))
    else:
        st.write("No entries in the last 7 days.")

# Load records
safe_preview("Pilot Coating", pcp_sheet.get_all_records(), "Date")
safe_preview("Dip Coating", dcp_sheet.get_all_records(), "Date")
safe_preview("Coater Tension", ct_sheet.get_all_records(), "PCoating_ID")  # Only if date is part of ID or in another field
safe_preview("Coating Solution Mass", csm_sheet.get_all_records(), "Date_Time")

