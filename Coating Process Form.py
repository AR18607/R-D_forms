import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import pandas as pd

# ---------------- CONFIG ----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_worksheet(sheet, title, headers):
    try:
        worksheet = sheet.worksheet(title)
        if worksheet.row_values(1) != headers:
            worksheet.clear()
            worksheet.append_row(headers)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=title, rows="1000", cols="50")
        worksheet.append_row(headers)
    return worksheet

def get_next_id(worksheet, id_column):
    records = worksheet.get_all_records()
    ids = [int(record[id_column]) for record in records if str(record[id_column]).isdigit()]
    return max(ids) + 1 if ids else 1

# ---------------- MAIN APP ----------------
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)
st.set_page_config(page_title="Coating Process Entry", layout="wide")
st.title("🧪 Coating Process Entry")

# ---------------- TABS ----------------
tabs = st.tabs(["Pilot Coating", "Dip Coating", "Coater Tension", "Solution Mass"])

# ================= TAB 1: PILOT COATING =================
with tabs[0]:
    st.subheader("🌬️ Pilot Coating Form")

    pcp_headers = [
        "PCoating_ID", "Solution ID", "Date", "Box_Temperature", "Box_RH", "N2_Flow",
        "Load_Cell_Slope", "Number_of_Fibers", "Coating_Speed", "Tower_1_Set_Point",
        "Tower_1_Entry_Temperature", "Tower_2_Set_Point", "Tower_2_Entry_Temperature",
        "Coating_Layer_Type", "Operator_Initials", "Ambient_Temperature", "Ambient_RH", "Notes"]

    pcp_sheet = get_or_create_worksheet(spreadsheet, "Pilot Coating Process Tbl", pcp_headers)

    solution_sheet = get_or_create_worksheet(spreadsheet, "Solution ID Tbl", ["Solution ID"])
    solution_ids = [r["Solution ID"] for r in solution_sheet.get_all_records()]

    with st.form("pilot_form", clear_on_submit=True):
        pcoating_id = get_next_id(pcp_sheet, "PCoating_ID")
        st.markdown(f"**Auto-generated PCoating ID:** `{pcoating_id}`")
        selected_solution_id = st.selectbox("Solution ID", solution_ids)
        date = st.date_input("Date")
        box_temperature = st.number_input("Box Temperature (\u00b0C)", min_value=0.0)
        box_rh = st.number_input("Box RH (%)", min_value=0.0)
        n2_flow = st.number_input("N2 Flow (L/min)", min_value=0.0)
        load_cell_slope = st.number_input("Load Cell Slope", min_value=0.0)
        number_of_fibers = st.number_input("Number of Fibers", min_value=0)
        coating_speed = st.number_input("Coating Speed (m/min)", min_value=0.0)
        tower1_set_point = st.number_input("Tower 1 Set Point (\u00b0C)", min_value=0.0)
        tower1_entry_temp = st.number_input("Tower 1 Entry Temperature (\u00b0C)", min_value=0.0)
        tower2_set_point = st.number_input("Tower 2 Set Point (\u00b0C)", min_value=0.0)
        tower2_entry_temp = st.number_input("Tower 2 Entry Temperature (\u00b0C)", min_value=0.0)
        coating_layer_type = st.selectbox("Coating Layer Type", ["GL", "AL", "PL"])
        operator_initials = st.text_input("Operator Initials")
        ambient_temp = st.number_input("Ambient Temperature (\u00b0C)", min_value=0.0)
        ambient_rh = st.number_input("Ambient RH (%)", min_value=0.0)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("✅ Submit Pilot Coating Entry")

    if submitted:
        pcp_sheet.append_row([
            pcoating_id, selected_solution_id, date.strftime("%Y-%m-%d"), box_temperature, box_rh,
            n2_flow, load_cell_slope, number_of_fibers, coating_speed, tower1_set_point,
            tower1_entry_temp, tower2_set_point, tower2_entry_temp, coating_layer_type,
            operator_initials, ambient_temp, ambient_rh, notes
        ])
        st.success(f"✅ Pilot Coating Entry {pcoating_id} saved successfully!")
