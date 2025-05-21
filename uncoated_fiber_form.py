import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
from datetime import datetime, timedelta

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

# ------------------ Uncoated Fiber Data Tbl ------------------ #
st.header("Uncoated Fiber Data Entry")

ufd_headers = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices","Notes", "Date_Time"
]

ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ufd_headers)

with st.form("Uncoated Fiber Data Form"):
    supplier_batch_id = st.text_input("Supplier Batch ID")
    inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", min_value=0)
    inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", min_value=0)
    outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", min_value=0)
    outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", min_value=0)
    reported_concentricity = st.number_input("Reported Concentricity (%)", min_value=0)
    batch_length = st.number_input("Batch Length (m)", min_value=0)
    shipment_date = st.date_input("Shipment Date")
    tracking_number = st.text_input("Tracking Number")
    fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"])
    average_t_od = st.number_input("Average t/OD", min_value=0.0)
    minimum_t_od = st.number_input("Minimum t/OD", min_value=0.0)
    minimum_wall_thickness = st.number_input("Minimum Wall Thickness (um)", min_value=0)
    average_wall_thickness = st.number_input("Average Wall Thickness (um)", min_value=0)
    n2_permeance = st.number_input("N2 Permeance (GPU)", min_value=0)
    collapse_pressure = st.number_input("Collapse Pressure (psi)", min_value=0)
    st.write("You entered:", collapse_pressure)  # Safe to use here


    kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", min_value=0.0)
    kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", min_value=0.0)
    order_on_bobbin = st.number_input("Order on Bobbin", min_value=0)
    number_of_blue_splices = st.number_input("Number of Blue Splices", min_value=0)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        batch_fiber_id = get_next_id(ufd_sheet, "Batch_Fiber_ID")
        ufd_sheet.append_row([
            batch_fiber_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
            outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
            shipment_date.strftime("%Y-%m-%d"), tracking_number, fiber_source, average_t_od,
            minimum_t_od, minimum_wall_thickness, average_wall_thickness, n2_permeance,
            collapse_pressure, kink_test_2_95, kink_test_2_36, order_on_bobbin,
            number_of_blue_splices, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        st.success(f"Uncoated Fiber Data with ID {batch_fiber_id} submitted successfully!")

# ------------------ UnCoatedSpool ID Tbl ------------------ #
st.header("UnCoatedSpool ID Entry")

usid_headers = ["UncoatedSpool_ID", "Type", "C_Length", "Date_Time"]
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", usid_headers)

with st.form("UnCoatedSpool ID Form"):
    spool_type = st.selectbox("Type", ["As received", "Combined"])
    c_length = st.number_input("C-Length (m)", min_value=0)

    submitted = st.form_submit_button("Submit")
    if submitted:
        uncoated_spool_id = get_next_id(usid_sheet, "UncoatedSpool_ID")
        usid_sheet.append_row([uncoated_spool_id, spool_type, c_length , datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        st.success(f"UnCoatedSpool ID {uncoated_spool_id} submitted successfully!")

# ------------------ As Received UnCoatedSpools Tbl ------------------ #
st.header("As Received UnCoatedSpools Entry")

ar_headers = ["Received_Spool_PK", "UncoatedSpool_ID", "Batch_Fiber_ID", "Notes", "Date_Time"]
ar_sheet = get_or_create_worksheet(spreadsheet, "As Received UnCoatedSpools Tbl", ar_headers)

# Fetch existing UncoatedSpool_IDs and Batch_Fiber_IDs for dropdowns
uncoated_spool_ids = [record["UncoatedSpool_ID"] for record in usid_sheet.get_all_records()]
batch_fiber_ids = [record["Batch_Fiber_ID"] for record in ufd_sheet.get_all_records()]

with st.form("As Received UnCoatedSpools Form"):
    selected_uncoated_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
    selected_batch_fiber_id = st.selectbox("Batch Fiber ID", batch_fiber_ids)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit")
    if submitted:
        received_spool_pk = get_next_id(ar_sheet, "Received_Spool_PK")
        ar_sheet.append_row([received_spool_pk, selected_uncoated_spool_id, selected_batch_fiber_id, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        st.success(f"As Received UnCoatedSpool with PK {received_spool_pk} submitted successfully!")

# ------------------ Combined Spools Tbl ------------------ #
st.header("Combined Spools Entry")

cs_headers = ["Combined_SpoolsPK", "UncoatedSpool_ID", "Received_Spool_PK", "Date_Time"]
cs_sheet = get_or_create_worksheet(spreadsheet, "Combined Spools Tbl", cs_headers)

# Fetch existing Received_Spool_PKs for dropdown
received_spool_pks = [record["Received_Spool_PK"] for record in ar_sheet.get_all_records()]

with st.form("Combined Spools Form"):
    selected_uncoated_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
    selected_received_spool_pk = st.selectbox("Received Spool PK", received_spool_pks)

    submitted = st.form_submit_button("Submit")
    if submitted:
        combined_spools_pk = get_next_id(cs_sheet, "Combined_SpoolsPK")
        cs_sheet.append_row([combined_spools_pk, selected_uncoated_spool_id, selected_received_spool_pk, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        st.success(f"Combined Spool with PK {combined_spools_pk} submitted successfully!")

# ------------------ Ardent Fiber Dimension QC Tbl ------------------ #
st.header("Ardent Fiber Dimension QC Entry")

qc_headers = [
    "Ardent_QC_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Ardent_QC_Inside_Diameter",
    "Ardent_QC_Outside_Diameter", "Measured_Concentricity", "Wall_Thickness",
    "Operator_Initials", "Notes", "Date_Time", "Inside_Circularity", "Outside_Circularity"
]
qc_sheet = get_or_create_worksheet(spreadsheet, "Ardent Fiber Dimension QC Tbl", qc_headers)

with st.form("Ardent Fiber Dimension QC Form"):
    selected_batch_fiber_id = st.selectbox("Batch Fiber ID", batch_fiber_ids)
    selected_uncoated_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
    ardent_qc_inside_diameter = st.number_input("Ardent QC Inside Diameter (um)", min_value=0)
    ardent_qc_outside_diameter = st.number_input("Ardent QC Outside Diameter (um)", min_value=0)
    measured_concentricity = st.number_input("Measured Concentricity (%)", min_value=0)
    wall_thickness = st.number_input("Wall Thickness (um)", min_value=0)
    operator_initials = st.text_input("Operator Initials")
    notes = st.text_area("Notes")
    date_time = st.date_input("Date")
    inside_circularity = st.number_input("Inside Circularity", min_value=0.0)
    outside_circularity = st.number_input("Outside Circularity", min_value=0.0)

    submitted = st.form_submit_button("Submit")
    if submitted:
        ardent_qc_id = get_next_id(qc_sheet, "Ardent_QC_ID")
        qc_sheet.append_row([
            ardent_qc_id, selected_batch_fiber_id, selected_uncoated_spool_id,
            ardent_qc_inside_diameter, ardent_qc_outside_diameter, measured_concentricity,
            wall_thickness, operator_initials, notes, date_time.strftime("%Y-%m-%d"),
            inside_circularity, outside_circularity
        ])
        st.success(f"Ardent Fiber QC Entry with ID {ardent_qc_id} submitted successfully!")


# ------------------ 7-DAYS DATA PREVIEW FOR ALL TABLES ------------------
st.markdown("## 📅 Last 7 Days Data Preview")

def parse_date(date_str):
    """Converts date string to a datetime object, handling multiple formats."""
    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None  # Return None if parsing fails

def filter_last_7_days(records, date_key, debug_title):
    """Filters records where `date_key` is within the last 7 days, with debug logging."""
    filtered_records = []
    today = datetime.today()

    st.markdown(f"#### 🔍 Debug: {debug_title} — Checking '{date_key}'")
    for record in records:
        date_str = record.get(date_key, "").strip()
        parsed_date = parse_date(date_str)
        st.write({
            "Raw": date_str,
            "Parsed": str(parsed_date),
            "Included": parsed_date.date() >= (today - timedelta(days=7)).date() if parsed_date else False
        })

        if parsed_date and parsed_date.date() >= (today - timedelta(days=7)).date():
            filtered_records.append(record)

    return filtered_records

# ------------------ Uncoated Fiber Data Tbl ------------------ #
st.markdown("### 🧪 Uncoated Fiber Data (Last 7 Days)")
ufd_records = ufd_sheet.get_all_records()
filtered_ufd = filter_last_7_days(ufd_records, "Date_Time", "Uncoated Fiber Data")
st.dataframe(pd.DataFrame(filtered_ufd) if filtered_ufd else "No records in the last 7 days.")

# ------------------ UnCoatedSpool ID Tbl ------------------ #
st.markdown("### 🧵 UnCoatedSpool ID (Last 7 Days)")
usid_records = usid_sheet.get_all_records()
filtered_usid = filter_last_7_days(usid_records, "Date_Time", "UnCoatedSpool ID")
st.dataframe(pd.DataFrame(filtered_usid) if filtered_usid else "No records in the last 7 days.")

# ------------------ As Received UnCoatedSpools Tbl ------------------ #
st.markdown("### 📦 As Received UnCoatedSpools (Last 7 Days)")
ar_records = ar_sheet.get_all_records()
filtered_ar = filter_last_7_days(ar_records, "Date_Time", "As Received UnCoatedSpools")
st.dataframe(pd.DataFrame(filtered_ar) if filtered_ar else "No records in the last 7 days.")

# ------------------ Combined Spools Tbl ------------------ #
st.markdown("### 🔗 Combined Spools (Last 7 Days)")
cs_records = cs_sheet.get_all_records()
filtered_cs = filter_last_7_days(cs_records, "Date_Time", "Combined Spools")
st.dataframe(pd.DataFrame(filtered_cs) if filtered_cs else "No records in the last 7 days.")

# ------------------ Ardent Fiber Dimension QC Tbl ------------------ #
st.markdown("### 🧪 Ardent Fiber Dimension QC (Last 7 Days)")
qc_records = qc_sheet.get_all_records()
filtered_qc = filter_last_7_days(qc_records, "Date_Time", "Ardent Fiber Dimension QC")
st.dataframe(pd.DataFrame(filtered_qc) if filtered_qc else "No records in the last 7 days.")
