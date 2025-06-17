# === IMPORTS ===
import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd

# === DISABLE ENTER KEY FORM SUBMIT ===
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# === GOOGLE SHEET SETUP ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
spreadsheet = client.open("R&D Data Form")

# === LOAD SYENSQO SHEET ===
syensqo_url = "https://docs.google.com/spreadsheets/d/1AGZ1g3LeSPtLAKV685snVQeERWXVPF4WlIAV8aAj9o8"
syensqo_sheet = client.open_by_url(syensqo_url).worksheet("Syensqo Data")
syensqo_df = pd.DataFrame(syensqo_sheet.get_all_records())

# === HELPER FUNCTIONS ===
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
    return 1

# === MAIN FORM SETUP ===
st.header("Uncoated Fiber Data Entry")
ufd_headers = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices",
    "Notes", "Date_Time"
]
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ufd_headers)

fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"])

data_entries = []

if fiber_source == "Syensqo":
    tracking_numbers = syensqo_df["Tracking number UPS"].dropna().unique().tolist()
    selected_tracking = st.selectbox("Select Tracking Number", tracking_numbers)

    selected_row = syensqo_df[syensqo_df["Tracking number UPS"] == selected_tracking].iloc[0]

    batch_fiber_id = get_next_id(ufd_sheet, "Batch_Fiber_ID")
    st.markdown(f"**Next Batch_Fiber_ID:** `{batch_fiber_id}`")

    with st.form("syensqo_entry_form"):
        st.text_input("Supplier Batch ID", value=selected_row.get("Batch ID", ""), key="batch")
        st.number_input("Inside Diameter Avg (um)", value=float(selected_row.get("Inside Diameter Avg", 0)), key="ida")
        st.number_input("Inside Diameter StDev (um)", value=float(selected_row.get("Inside Diameter Stdev", 0)), key="ids")
        st.number_input("Outside Diameter Avg (um)", value=float(selected_row.get("Outside Diameter Avg", 0)), key="oda")
        st.number_input("Outside Diameter StDev (um)", value=float(selected_row.get("Outside Diameter Stdev", 0)), key="ods")
        st.number_input("Reported Concentricity (%)", value=float(selected_row.get("Reported concentricity", 0)), key="rc")
        st.number_input("Batch Length (m)", value=float(selected_row.get("Batch Length (m)", 0)), key="bl")
        st.date_input("Shipment Date", value=datetime.today(), key="sd")
        st.text_input("Tracking Number", value=selected_row.get("Tracking number UPS", ""), key="tn")
        st.number_input("Average t/OD", value=0.0, key="atod")
        st.number_input("Minimum t/OD", value=0.0, key="mtod")
        st.number_input("Minimum Wall Thickness (um)", value=0, key="mwt")
        st.number_input("Average Wall Thickness (um)", value=0, key="awt")
        st.number_input("N2 Permeance (GPU)", value=0, key="n2")
        st.number_input("Collapse Pressure (psi)", value=0, key="cp")
        st.number_input("Kink Test 2.95 (mm)", value=0.0, key="kt295")
        st.number_input("Kink Test 2.36 (mm)", value=0.0, key="kt236")
        st.number_input("Order on Bobbin", value=0, key="bob")
        st.number_input("Number of Blue Splices", value=0, key="blue")
        notes = st.text_area("Notes")

        submit = st.form_submit_button("Submit")
        if submit:
            row_data = [
                batch_fiber_id, selected_row.get("Batch ID", ""), selected_row.get("Inside Diameter Avg", 0),
                selected_row.get("Inside Diameter Stdev", 0), selected_row.get("Outside Diameter Avg", 0),
                selected_row.get("Outside Diameter Stdev", 0), selected_row.get("Reported concentricity", 0),
                selected_row.get("Batch Length (m)", 0), datetime.today().strftime("%Y-%m-%d"),
                selected_row.get("Tracking number UPS", ""), "Syensqo", 0.0, 0.0, 0, 0, 0, 0, 0.0, 0.0, 0, 0,
                notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
            ufd_sheet.append_row(row_data)
            st.success(f"✅ Batch_Fiber_ID {batch_fiber_id} submitted successfully.")
