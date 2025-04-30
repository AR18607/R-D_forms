import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'path_to_your_service_account.json'  # Replace with your service account file path
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1uPdUWiiwMdJCYJaxZ5TneFa9h6tbSrs327BVLT5GVPY/edit#gid=0'  # Replace with your spreadsheet URL

# --- Authentication ---
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open_by_url(SPREADSHEET_URL)

# --- Helper Functions ---
def get_worksheet(name, headers):
    try:
        worksheet = spreadsheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=name, rows="1000", cols=str(len(headers)))
        worksheet.append_row(headers)
    return worksheet

def append_data(worksheet, data):
    worksheet.append_row(data)

# --- Streamlit App ---
st.title("Uncoated Fiber Data Entry Form")

# --- Uncoated Fiber Data Table ---
st.header("1. Uncoated Fiber Data")
fiber_data_headers = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices", "Notes"
]
fiber_data_ws = get_worksheet("Uncoated_Fiber_Data_Tbl", fiber_data_headers)

with st.form("fiber_data_form"):
    supplier_batch_id = st.text_input("Supplier Batch ID")
    inside_diameter_avg = st.number_input("Inside Diameter Avg (μm)", step=1)
    inside_diameter_stdev = st.number_input("Inside Diameter StDev (μm)", step=1)
    outside_diameter_avg = st.number_input("Outside Diameter Avg (μm)", step=1)
    outside_diameter_stdev = st.number_input("Outside Diameter StDev (μm)", step=1)
    reported_concentricity = st.number_input("Reported Concentricity (%)", step=1)
    batch_length = st.number_input("Batch Length (m)", step=1)
    shipment_date = st.date_input("Shipment Date")
    tracking_number = st.text_input("Tracking Number")
    fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"])
    average_t_od = st.number_input("Average t/OD", format="%.2f")
    minimum_t_od = st.number_input("Minimum t/OD", format="%.2f")
    minimum_wall_thickness = st.number_input("Minimum Wall Thickness (μm)", step=1)
    average_wall_thickness = st.number_input("Average Wall Thickness (μm)", step=1)
    n2_permeance = st.number_input("N2 Permeance (GPU)", step=1)
    collapse_pressure = st.number_input("Collapse Pressure (psi)", step=1)
    kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", format="%.2f")
    kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", format="%.2f")
    order_on_bobbin = st.number_input("Order on Bobbin", step=1)
    number_of_blue_splices = st.number_input("Number of Blue Splices", step=1)
    notes = st.text_area("Notes")
    submit_fiber_data = st.form_submit_button("Submit Uncoated Fiber Data")

    if submit_fiber_data:
        new_id = len(fiber_data_ws.get_all_values())  # Simple ID generation
        data = [
            new_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
            outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
            shipment_date.strftime("%Y-%m-%d"), tracking_number, fiber_source, average_t_od, minimum_t_od,
            minimum_wall_thickness, average_wall_thickness, n2_permeance, collapse_pressure,
            kink_test_2_95, kink_test_2_36, order_on_bobbin, number_of_blue_splices, notes
        ]
        append_data(fiber_data_ws, data)
        st.success("Uncoated Fiber Data submitted successfully!")

# --- UnCoated Spool ID Table ---
st.header("2. UnCoated Spool ID")
spool_id_headers = ["UncoatedSpool_ID", "Type", "C_Length"]
spool_id_ws = get_worksheet("UnCoatedSpool_ID_Tbl", spool_id_headers)

with st.form("spool_id_form"):
    spool_type = st.selectbox("Type", ["As received", "Combined"])
    c_length = st.number_input("C-Length (sum of batch lengths)", step=1)
    submit_spool_id = st.form_submit_button("Submit UnCoated Spool ID")

    if submit_spool_id:
        new_id = len(spool_id_ws.get_all_values())
        data = [new_id, spool_type, c_length]
        append_data(spool_id_ws, data)
        st.success("UnCoated Spool ID submitted successfully!")

# --- As Received UnCoated Spools Table ---
st.header("3. As Received UnCoated Spools")
as_received_headers = ["Received_Spool_PK", "UncoatedSpool_ID", "Batch_Fiber_ID", "Notes"]
as_received_ws = get_worksheet("As_Received_UnCoatedSpools_Tbl", as_received_headers)

with st.form("as_received_form"):
    uncoated_spool_id = st.number_input("Uncoated Spool ID", step=1)
    batch_fiber_id = st.number_input("Batch Fiber ID", step=1)
    notes = st.text_area("Notes")
    submit_as_received = st.form_submit_button("Submit As Received UnCoated Spool")

    if submit_as_received:
        new_id = len(as_received_ws.get_all_values())
        data = [new_id, uncoated_spool_id, batch_fiber_id, notes]
        append_data(as_received_ws, data)
        st.success("As Received UnCoated Spool submitted successfully!")

# --- Combined Spools Table ---
st.header("4. Combined Spools")
combined_spools_headers = ["Combined_SpoolsPK", "UncoatedSpool_ID", "Received_Spool_PK"]
combined_spools_ws = get_worksheet("Combined_Spools_Tbl", combined_spools_headers)

with st.form("combined_spools_form"):
    uncoated_spool_id = st.number_input("Uncoated Spool ID", step=1)
    received_spool_pk = st.number_input("Received Spool PK", step=1)
    submit_combined_spools = st.form_submit_button("Submit Combined Spool")

    if submit_combined_spools:
        new_id = len(combined_spools_ws.get_all_values())
        data = [new_id, uncoated_spool_id, received_spool_pk]
        append_data(combined_spools_ws, data)
        st.success("Combined Spool submitted successfully!")

# --- Ardent Fiber Dimension QC Table ---
st.header("5. Ardent Fiber Dimension QC")
ardent_qc_headers = [
    "Ardent_QC_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Ardent_QC_Inside_Diameter",
    "Ardent_QC_Outside_Diameter", "Measured_Concentricity", "Wall_Thickness",
    "Operator_Initials", "Notes", "Date_Time", "Inside_Circularity", "Outside_Circularity"
]
ardent_qc_ws = get_worksheet("Ardent_Fiber_Dimension_QC_Tbl", ardent_qc_headers)

with st.form("ardent_qc_form"):
    batch_fiber_id = st.number_input("Batch Fiber ID", step=1)
    uncoated_spool_id = st.number_input("Uncoated Spool ID", step=1)
    ardent_qc_inside_diameter = st.number_input("Ardent QC Inside Diameter (μm)", step=1)
    ardent_qc_outside_diameter = st.number_input("Ardent QC Outside Diameter (μm)", step=1)
    measured_concentricity = st.number_input("Measured Concentricity (%)", step=1)
    wall_thickness = st.number_input("Wall Thickness (μm)", step=1)
    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    date_time = st.date_input("Date")
    inside_circularity = st.number_input("Inside Circularity", format="%.2f")
    outside_circularity = st.number_input("Outside Circularity", format="%.2f")
    submit_ardent_qc = st.form_submit_button("Submit Ardent Fiber Dimension QC")

    if submit_ardent_qc:
        new_id = len(ardent_qc_ws.get_all_values())
        data = [
            new_id,  # Ardent QC ID
            batch_fiber_id,
            uncoated_spool_id,
            ardent_qc_inside_diameter,
            ardent_qc_outside_diameter,
            measured_concentricity,
            wall_thickness,
            operator_initials,
            notes,
            str(date_time),
            inside_circularity,
            outside_circularity
        ]
        ardent_qc_ws.append_row(data)
        st.success("✅ Ardent Fiber Dimension QC entry saved successfully!")
