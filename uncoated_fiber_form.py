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

def parse_float(val):
    try:
        return float(str(val).strip().replace(",", "").replace("%", ""))
    except:
        return 0.0

def parse_str(val):
    return str(val).strip() if val else ""

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

ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ufd_headers)
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", usid_headers)
uncoated_spool_ids = [record["UncoatedSpool_ID"] for record in usid_sheet.get_all_records()]

# === FILE UPLOAD AND DATA MAPPING ===
st.header("Uncoated Fiber Data Entry")
st.markdown(f"**Next Batch_Fiber_ID:** {get_next_id(ufd_sheet, 'Batch_Fiber_ID')}")

uploaded_file = st.file_uploader("Upload Syensqo Vendor File (Excel only)", type=["xlsx"])
prefill_data = []

column_map = {
    "Supplier_Batch_ID": "Tracking number UPS",
    "Inside_Diameter_Avg": "ID",
    "Inside_Diameter_StDev": "ID SD",
    "Outside_Diameter_Avg": "OD",
    "Outside_Diameter_StDev": "OD SD",
    "Reported_Concentricity": "Concentricity (%)",
    "Batch_Length": "Batch length (m)",
    "Shipment_Date": "Shipment date",
    "Tracking_Number": "Tracking number UPS",
    "Average_t_OD": "Thickness/OD",
    "Minimum_t_OD": "minimum thickness/OD",
    "Minimum_Wall_Thickness": "Thickness (µm)",
    "N2_Permeance": "GPU (N2)",
    "Collapse_Pressure": "Collapse pressure (PSI)",
    "Kink_Test_2_95": "Kink test 2.95 inches (mm)",
    "Kink_Test_2_36": "Kink test 2.36 inches (mm)",
    "Order_On_Bobbin": "Bobbin number",
    "Number_Of_Blue_Splices": "Blue Splicings number"
}

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    for _, row in df.iterrows():
        record = {key: parse_str(row.get(src, "")) for key, src in column_map.items()}
        prefill_data.append(record)

batch_count = st.number_input("Number of batches to enter", min_value=1, value=max(1, len(prefill_data)))

for i in range(batch_count):
    st.subheader(f"Batch Entry #{i+1}")
    data = prefill_data[i] if i < len(prefill_data) else {}
    with st.form(f"fiber_form_{i}"):
        supplier_batch_id = st.text_input("Supplier Batch ID", value=data.get("Supplier_Batch_ID", ""))
        inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", value=parse_float(data.get("Inside_Diameter_Avg", 0)))
        inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", value=parse_float(data.get("Inside_Diameter_StDev", 0)))
        outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", value=parse_float(data.get("Outside_Diameter_Avg", 0)))
        outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", value=parse_float(data.get("Outside_Diameter_StDev", 0)))
        reported_concentricity = st.number_input("Reported Concentricity (%)", value=parse_float(data.get("Reported_Concentricity", 0)))
        batch_length = st.number_input("Batch Length (m)", value=parse_float(data.get("Batch_Length", 0)))
        shipment_date = st.date_input("Shipment Date", value=datetime.today())
        tracking_number = st.text_input("Tracking Number", value=data.get("Tracking_Number", ""))
        fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"], index=1)
        average_t_od = st.number_input("Average t/OD", value=parse_float(data.get("Average_t_OD", 0)))
        minimum_t_od = st.number_input("Minimum t/OD", value=parse_float(data.get("Minimum_t_OD", 0)))
        minimum_wall_thickness = st.number_input("Minimum Wall Thickness (um)", value=parse_float(data.get("Minimum_Wall_Thickness", 0)))
        average_wall_thickness = st.number_input("Average Wall Thickness (um)", value=0.0)
        n2_permeance = st.number_input("N2 Permeance (GPU)", value=parse_float(data.get("N2_Permeance", 0)))
        collapse_pressure = st.number_input("Collapse Pressure (psi)", value=parse_float(data.get("Collapse_Pressure", 0)))
        kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", value=parse_float(data.get("Kink_Test_2_95", 0)))
        kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", value=parse_float(data.get("Kink_Test_2_36", 0)))
        order_on_bobbin = st.number_input("Order on Bobbin", value=parse_float(data.get("Order_On_Bobbin", 0)))
        number_of_blue_splices = st.number_input("Number of Blue Splices", value=parse_float(data.get("Number_Of_Blue_Splices", 0)))
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
                collapse_pressure, kink_test_2_95, kink_test_2_36, int(order_on_bobbin), int(number_of_blue_splices),
                selected_spool_id, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
            st.success(f"Batch {batch_fiber_id} submitted successfully!")
