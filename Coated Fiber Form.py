import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
spreadsheet = client.open("R&D Data Form")

# Helpers
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

# ------------------ Coated Spool Tbl ------------------ #
st.header("Coated Spool Entry")

cs_headers = ["CoatedSpool_ID", "UnCoatedSpool_ID"]
cs_sheet = get_or_create_worksheet(spreadsheet, "Coated Spool Tbl", cs_headers)

# Load FK values
uncoated_spool_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", ["UncoatedSpool_ID", "Type", "C_Length"])
uncoated_spool_ids = [str(record["UncoatedSpool_ID"]) for record in uncoated_spool_sheet.get_all_records()]

with st.form("Coated Spool Form"):
    selected_uncoated_spool_id = st.selectbox("UnCoatedSpool ID", uncoated_spool_ids)
    submitted = st.form_submit_button("Submit")
    if submitted:
        coated_spool_id = get_next_id(cs_sheet, "CoatedSpool_ID")
        cs_sheet.append_row([coated_spool_id, selected_uncoated_spool_id])
        st.success(f"Coated Spool with ID {coated_spool_id} submitted successfully!")

# ------------------ Fiber per Coating Run Tbl ------------------ #
st.header("Fiber Per Coating Run Entry")

fpcr_headers = [
    "FiberCoat_ID", "PCoating_ID", "CoatedSpool_ID",
    "Payout_Position", "Length_Coated", "Label", "Notes"
]
fpcr_sheet = get_or_create_worksheet(spreadsheet, "Fiber per Coating Run Tbl (Coating)", fpcr_headers)

# FK values
pcoating_sheet = get_or_create_worksheet(spreadsheet, "Pilot Coating Process Tbl", ["PCoating_ID"])
pcoating_ids = [str(record["PCoating_ID"]) for record in pcoating_sheet.get_all_records()]
coated_spool_ids = [str(record["CoatedSpool_ID"]) for record in cs_sheet.get_all_records()]

with st.form("Fiber Per Coating Run Form"):
    selected_pcoating_id = st.selectbox("PCoating ID", pcoating_ids)
    selected_coated_spool_id = st.selectbox("CoatedSpool ID", coated_spool_ids)
    payout_position = st.text_input("Payout Position")
    length_coated = st.number_input("Length Coated (m)", min_value=0.0)
    label = st.text_input("Label")
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        fibercoat_id = get_next_id(fpcr_sheet, "FiberCoat_ID")
        fpcr_sheet.append_row([
            fibercoat_id, selected_pcoating_id, selected_coated_spool_id,
            payout_position, length_coated, label, notes
        ])
        st.success(f"Fiber Per Coating Run with ID {fibercoat_id} submitted successfully!")
