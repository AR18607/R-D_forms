import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
from google.oauth2.service_account import Credentials

# Load credentials from Streamlit secrets
creds_info = json.loads(st.secrets["gcp_service_account"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_info, scopes=scope)




# Replace with your actual Google Sheet name
SPREADSHEET_NAME = "R&D Data Form"
spreadsheet = client.open(SPREADSHEET_NAME)

# ---------------------------
# Helper Function to Get or Create Worksheet
# ---------------------------
def get_or_create_worksheet(sheet, title, headers):
    try:
        worksheet = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=title, rows="1000", cols="50")
        worksheet.append_row(headers)
    return worksheet

# ---------------------------
# Define Headers for Each Worksheet
# ---------------------------
uncoated_fiber_headers = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices", "Notes"
]

uncoated_spool_headers = ["UncoatedSpool_ID", "Type", "C_Length"]

as_received_headers = ["Received_Spool_PK", "UncoatedSpool_ID", "Batch_Fiber_ID", "Notes"]

combined_spools_headers = ["Combined_SpoolsPK", "UncoatedSpool_ID", "Received_Spool_PK"]

ardent_qc_headers = [
    "Ardent_QC_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Ardent_QC_Inside_Diameter",
    "Ardent_QC_Outside_Diameter", "Measured_Concentricity", "Wall_Thickness", "Operator_Initials",
    "Notes", "Date_Time", "Inside_Circularity", "Outside_Circularity"
]

# ---------------------------
# Initialize Worksheets
# ---------------------------
uncoated_fiber_ws = get_or_create_worksheet(spreadsheet, "Uncoated_Fiber_Data_Tbl", uncoated_fiber_headers)
uncoated_spool_ws = get_or_create_worksheet(spreadsheet, "UnCoatedSpool_ID_Tbl", uncoated_spool_headers)
as_received_ws = get_or_create_worksheet(spreadsheet, "As_Received_UnCoatedSpools_Tbl", as_received_headers)
combined_spools_ws = get_or_create_worksheet(spreadsheet, "Combined_Spools_Tbl", combined_spools_headers)
ardent_qc_ws = get_or_create_worksheet(spreadsheet, "Ardent_Fiber_Dimension_QC_Tbl", ardent_qc_headers)

# ---------------------------
# Streamlit Form
# ---------------------------
st.title("Uncoated Fiber Form")

with st.form("uncoated_fiber_form"):
    st.subheader("Uncoated Fiber Data")

    supplier_batch_id = st.text_input("Supplier Batch ID")
    inside_diameter_avg = st.number_input("Inside Diameter (um) Avg", min_value=0)
    inside_diameter_stdev = st.number_input("Inside Diameter (um) StDev", min_value=0)
    outside_diameter_avg = st.number_input("Outside Diameter (um) Avg", min_value=0)
    outside_diameter_stdev = st.number_input("Outside Diameter (um) StDev", min_value=0)
    reported_concentricity = st.number_input("Reported Concentricity (%)", min_value=0)
    batch_length = st.number_input("Batch Length (m)", min_value=0)
    shipment_date = st.date_input("Shipment Date")
    tracking_number = st.text_input("Tracking Number")
    fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"])
    average_t_od = st.number_input("Average t/OD", min_value=0.0, format="%.2f")
    minimum_t_od = st.number_input("Minimum t/OD", min_value=0.0, format="%.2f")
    minimum_wall_thickness = st.number_input("Minimum Wall Thickness (um)", min_value=0)
    average_wall_thickness = st.number_input("Average Wall Thickness (um)", min_value=0)
    n2_permeance = st.number_input("N2 Permeance (GPU)", min_value=0)
    collapse_pressure = st.number_input("Collapse Pressure (psi)", min_value=0)
    kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", min_value=0.0, format="%.2f")
    kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", min_value=0.0, format="%.2f")
    order_on_bobbin = st.number_input("Order on Bobbin (outside = 1)", min_value=0)
    number_of_blue_splices = st.number_input("Number of Blue Splices", min_value=0)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")

    if submitted:
        # Generate a new Batch_Fiber_ID
        existing_ids = uncoated_fiber_ws.col_values(1)[1:]  # Exclude header
        if existing_ids:
            new_id = max([int(i) for i in existing_ids if i.isdigit()]) + 1
        else:
            new_id = 1

        new_row = [
            new_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
            outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
            shipment_date.strftime("%Y-%m-%d"), tracking_number, fiber_source, average_t_od,
            minimum_t_od, minimum_wall_thickness, average_wall_thickness, n2_permeance,
            collapse_pressure, kink_test_2_95, kink_test_2_36, order_on_bobbin,
            number_of_blue_splices, notes
        ]

        uncoated_fiber_ws.append_row(new_row)
        st.success(f"Data submitted successfully with Batch_Fiber_ID: {new_id}")
