# === IMPORTS ===
import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# === DISABLE ENTER TO SUBMIT ===
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# === GOOGLE SHEET CONFIG ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
spreadsheet = client.open("R&D Data Form")

# === UTILS ===
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

def parse_date(date_str):
    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            continue
    return None

def filter_last_7_days(records, date_key):
    today = datetime.today()
    filtered = []
    for record in records:
        date_str = record.get(date_key, "").strip()
        parsed = parse_date(date_str)
        if parsed and parsed.date() >= (today - timedelta(days=7)).date():
            filtered.append(record)
    return filtered

# === HEADERS ===
ufd_headers = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices",
    "UncoatedSpool_ID", "Notes", "Date_Time"
]
usid_headers = ["UncoatedSpool_ID", "Type", "C_Length", "Date_Time"]
ar_headers = ["Received_Spool_PK", "UncoatedSpool_ID", "Batch_Fiber_ID", "Notes", "Date_Time"]
cs_headers = ["Combined_SpoolsPK", "UncoatedSpool_ID", "Received_Spool_PK", "Date_Time"]
qc_headers = [
    "Ardent_QC_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Ardent_QC_Inside_Diameter",
    "Ardent_QC_Outside_Diameter", "Measured_Concentricity", "Wall_Thickness",
    "Operator_Initials", "Notes", "Date_Time", "Inside_Circularity", "Outside_Circularity"
]

# === SHEETS ===
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ufd_headers)
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", usid_headers)
ar_sheet = get_or_create_worksheet(spreadsheet, "As Received UncoatedSpools Tbl", ar_headers)
cs_sheet = get_or_create_worksheet(spreadsheet, "Combined Spools Tbl", cs_headers)
qc_sheet = get_or_create_worksheet(spreadsheet, "Ardent Fiber Dimension QC Tbl", qc_headers)

# === FETCH EXISTING VALUES ===
uncoated_spool_ids = [record["UncoatedSpool_ID"] for record in usid_sheet.get_all_records()]
batch_fiber_ids = [record["Batch_Fiber_ID"] for record in ufd_sheet.get_all_records()]
received_spool_pks = [record["Received_Spool_PK"] for record in ar_sheet.get_all_records()]

# === UNCOATED FIBER DATA ENTRY ===
st.header("Uncoated Fiber Data Entry")
st.markdown(f"**Next Batch_Fiber_ID:** {get_next_id(ufd_sheet, 'Batch_Fiber_ID')}")

uploaded_file = st.file_uploader("Upload vendor sheet (optional, Excel only)", type=["xlsx"])
prefill_data = []

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    prefill_data = df.to_dict("records")

batch_count = st.number_input("Number of batches to enter", min_value=1, value=1)

for i in range(batch_count):
    st.subheader(f"Batch Entry #{i+1}")
    data = prefill_data[i] if i < len(prefill_data) else {}
    with st.form(f"fiber_form_{i}"):
        supplier_batch_id = st.text_input("Supplier Batch ID", value=data.get("Tracking number UPS", ""))
        inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", min_value=0.0, value=0.0)
        inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", min_value=0.0, value=0.0)
        outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", min_value=0.0, value=0.0)
        outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", min_value=0.0, value=0.0)
        reported_concentricity = st.number_input("Reported Concentricity (%)", min_value=0.0, value=0.0)
        batch_length = st.number_input("Batch Length (m)", min_value=0.0, value=float(data.get("Batch length (m)", 0)))
        shipment_date = st.date_input("Shipment Date", value=datetime.today())
        tracking_number = st.text_input("Tracking Number", value=data.get("Tracking number UPS", ""))
        fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"])
        average_t_od = st.number_input("Average t/OD", min_value=0.0, value=0.0)
        minimum_t_od = st.number_input("Minimum t/OD", min_value=0.0, value=0.0)
        minimum_wall_thickness = st.number_input("Minimum Wall Thickness (um)", min_value=0.0, value=0.0)
        average_wall_thickness = st.number_input("Average Wall Thickness (um)", min_value=0.0, value=0.0)
        n2_permeance = st.number_input("N2 Permeance (GPU)", min_value=0.0, value=0.0)
        collapse_pressure = st.number_input("Collapse Pressure (psi)", min_value=0.0, value=0.0)
        kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", min_value=0.0, value=0.0)
        kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", min_value=0.0, value=0.0)
        order_on_bobbin = st.number_input("Order on Bobbin", min_value=0, value=0)
        number_of_blue_splices = st.number_input("Number of Blue Splices", min_value=0, value=0)
        selected_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Submit Batch")
        if submitted:
            batch_fiber_id = get_next_id(ufd_sheet, "Batch_Fiber_ID")
            ufd_sheet.append_row([
                batch_fiber_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
                outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
                shipment_date.strftime("%Y-%m-%d"), tracking_number, fiber_source, average_t_od,
                minimum_t_od, minimum_wall_thickness, average_wall_thickness, n2_permeance,
                collapse_pressure, kink_test_2_95, kink_test_2_36, order_on_bobbin,
                number_of_blue_splices, selected_spool_id, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
            st.success(f"Batch {batch_fiber_id} submitted successfully!")
