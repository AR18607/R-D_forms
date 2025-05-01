import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Set up Google Sheets API credentials
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)

# Open the Google Sheet
spreadsheet = client.open("R&D Data Form")

# Function to get or create a worksheet
def get_or_create_worksheet(sheet, title, headers):
    try:
        worksheet = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=title, rows="1000", cols="50")
        worksheet.append_row(headers)
    return worksheet

# Function to get the next ID
def get_next_id(worksheet, id_column):
    records = worksheet.get_all_records()
    if records:
        last_id = max([int(record[id_column]) for record in records if str(record[id_column]).isdigit()])
        return last_id + 1
    else:
        return 1

# ------------------ Load Reference Data ------------------ #
# Load Solution IDs
solution_sheet = get_or_create_worksheet(spreadsheet, "Solution ID Tbl", ["Solution_ID"])
solution_ids = [record["Solution_ID"] for record in solution_sheet.get_all_records()]

# Load Batch Fiber IDs
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ["Batch_Fiber_ID"])
batch_fiber_ids = [record["Batch_Fiber_ID"] for record in ufd_sheet.get_all_records()]

# Load Uncoated Spool IDs
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", ["UncoatedSpool_ID"])
uncoated_spool_ids = [record["UncoatedSpool_ID"] for record in usid_sheet.get_all_records()]

# ------------------ Pilot Coating Process Entry ------------------ #
st.header("Pilot Coating Process Entry")

pcp_headers = [
    "PCoating_ID", "Solution_ID", "Date", "Box_Temperature", "Box_RH", "N2_Flow",
    "Load_Cell_Slope", "Number_of_Fibers", "Coating_Speed", "Tower_1_Set_Point",
    "Tower_1_Entry_Temperature", "Tower_2_Set_Point", "Tower_2_Entry_Temperature",
    "Coating_Layer_Type", "Operator_Initials", "Ambient_Temperature", "Ambient_RH", "Notes"
]
pcp_sheet = get_or_create_worksheet(spreadsheet, "Pilot Coating Process Tbl", pcp_headers)

with st.form("Pilot Coating Process Form"):
    selected_solution_id = st.selectbox("Solution ID", solution_ids)
    date = st.date_input("Date")
    box_temperature = st.number_input("Box Temperature (°C)", min_value=0.0)
    box_rh = st.number_input("Box RH (%)", min_value=0.0)
    n2_flow = st.number_input("N2 Flow (L/min)", min_value=0.0)
    load_cell_slope = st.number_input("Load Cell Slope", min_value=0.0)
    number_of_fibers = st.number_input("Number of Fibers", min_value=0)
    coating_speed = st.number_input("Coating Speed (m/min)", min_value=0.0)
    tower1_set_point = st.number_input("Tower 1 Set Point (°C)", min_value=0.0)
    tower1_entry_temp = st.number_input("Tower 1 Entry Temperature (°C)", min_value=0.0)
    tower2_set_point = st.number_input("Tower 2 Set Point (°C)", min_value=0.0)
    tower2_entry_temp = st.number_input("Tower 2 Entry Temperature (°C)", min_value=0.0)
    coating_layer_type = st.selectbox("Coating Layer Type", ["GL", "AL", "PL"])
    operator_initials = st.text_input("Operator Initials")
    ambient_temp = st.number_input("Ambient Temperature (°C)", min_value=0.0)
    ambient_rh = st.number_input("Ambient RH (%)", min_value=0.0)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        pcoating_id = get_next_id(pcp_sheet, "PCoating_ID")
        pcp_sheet.append_row([
            pcoating_id, selected_solution_id, date.strftime("%Y-%m-%d"), box_temperature, box_rh,
            n2_flow, load_cell_slope, number_of_fibers, coating_speed, tower1_set_point,
            tower1_entry_temp, tower2_set_point, tower2_entry_temp, coating_layer_type,
            operator_initials, ambient_temp, ambient_rh, notes
        ])
        st.success(f"Pilot Coating Process Entry with ID {pcoating_id} submitted successfully!")

# ------------------ Dip Coating Process Entry ------------------ #
st.header("Dip Coating Process Entry")

dcp_headers = [
    "DCoating_ID", "Solution_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Date", "Box_Temperature",
    "Box_RH", "N2_Flow", "Number_of_Fibers", "Coating_Speed", "Annealing_Time",
    "Annealing_Temperature", "Coating_Layer_Type", "Operator_Initials", "Ambient_Temperature",
    "Ambient_RH", "Notes"
]
dcp_sheet = get_or_create_worksheet(spreadsheet, "Dip Coating Process Tbl", dcp_headers)

with st.form("Dip Coating Process Form"):
    selected_solution_id = st.selectbox("Solution ID", solution_ids)
    selected_batch_fiber_id = st.selectbox("Batch Fiber ID", batch_fiber_ids)
    selected_uncoated_spool_id = st.selectbox("Uncoated Spool ID", uncoated_spool_ids)
    date = st.date_input("Date")
    box_temperature = st.number_input("Box Temperature (°C)", min_value=0.0)
    box_rh = st.number_input("Box RH (%)", min_value=0.0)
    n2_flow = st.number_input("N2 Flow (L/min)", min_value=0.0)
    number_of_fibers = st.number_input("Number of Fibers", min_value=0)
    coating_speed = st.number_input("Coating Speed (m/min)", min_value=0.0)
    annealing_time = st.number_input("Annealing Time (min)", min_value=0.0)
    annealing_temp = st.number_input("Annealing Temperature (°C)", min_value=0.0)
    coating_layer_type = st.selectbox("Coating Layer Type", ["GL", "AL", "PL"])
    operator_initials = st.text_input("Operator Initials")
    ambient_temp = st.number_input("Ambient Temperature (°C)", min_value=0.0)
    ambient_rh = st.number_input("Ambient RH (%)", min_value=0.0)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        dcoating_id = get_next_id(dcp_sheet, "DCoating_ID")
        dcp_sheet.append_row([
            dcoating_id, selected_solution_id, selected_batch_fiber_id, selected_uncoated_spool_id,
            date.strftime("%Y-%m-%d"), box_temperature, box_rh, n2_flow, number_of_fibers,
            coating_speed, annealing_time, annealing_temp, coating_layer_type, operator_initials,
            ambient_temp, ambient_rh, notes
        ])
        st.success(f"Dip Coating Process Entry with ID {dcoating_id} submitted successfully!")

# ------------------ Coater Tension Entry ------------------ #
st.header("Coater Tension Entry")

ct_headers = ["Tension_ID", "PCoating_ID", "Payout_Location", "Tension", "Notes"]
ct_sheet = get_or_create_worksheet(spreadsheet, "Coater Tension Tbl", ct_headers)

# Fetch existing PCoating_IDs for dropdown
pcoating_ids = [record["PCoating_ID"] for record in pcp_sheet.get_all_records()]

with st.form("Coater Tension Form"):
    selected_pcoating_id = st.selectbox("PCoating ID", pcoating_ids)
    payout_location = st.text_input("Payout Location")
    tension = st.number_input("Tension (g)", min_value=0.0)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        tension_id = get_next_id(ct_sheet, "Tension_ID")
        ct_sheet.append_row([tension_id, selected_pcoating_id, payout_location, tension, notes])
        st.success(f"Coater Tension Entry with ID {tension_id} submitted successfully!")

# ------------------ Coating Solution Mass Entry ------------------ #
st.header("Coating Solution Mass Entry")

csm_headers = [
    "SolutionMass_ID", "Solution_ID", "Date_Time", "DCoating_ID", "PCoating_ID",
    "Solution_Mass", "Operators_Initials", "Notes"
]
csm_sheet = get_or_create_worksheet(spreadsheet, "Coating Solution Mass Tbl", csm_headers)

# Fetch existing DCoating_IDs and PCoating_IDs for dropdowns
dcoating_ids = [record["DCoating_ID"] for record in dcp_sheet.get_all_records()]
pcoating_ids = [record["PCoating_ID"] for record in pcp_sheet.get_all_records()]

with st.form("Coating Solution Mass Form"):
    selected_solution_id = st.selectbox("Solution ID", solution_ids)
    date_time = st.date_input("Date")
    selected_dcoating_id = st.selectbox("DCoating ID", dcoating_ids)
    selected_pcoating_id = st.selectbox("PCoating ID", pcoating_ids)
    solution_mass = st.number_input("Solution Mass (g)", min_value=0.0)
    operators_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        solution_mass_id = get_next_id(csm_sheet, "SolutionMass_ID")
        csm_sheet.append_row([
            solution_mass_id,
            selected_solution_id,
            date_time.strftime("%Y-%m-%d"),
            selected_dcoating_id,
            selected_pcoating_id,
            solution_mass,
            operators_initials,
            notes
        ])
        st.success(f"Coating Solution Mass Entry with ID {solution_mass_id} submitted successfully!")

