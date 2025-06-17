# === IMPORTS ===
import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIG ===
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
json_key = json.loads(st.secrets["gcp_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(json_key, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("R&D Data Form")

# === HELPERS ===
def get_or_create_worksheet(sheet, title, headers):
    try:
        ws = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows="1000", cols="50")
        ws.append_row(headers)
    return ws

def get_next_id(ws, col):
    data = ws.get_all_records()
    valid_ids = [int(r[col]) for r in data if str(r[col]).isdigit()]
    return max(valid_ids) + 1 if valid_ids else 1

def parse_date(date_str):
    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            continue
    return None

def filter_last_7_days(records, date_key):
    today = datetime.today().date()
    return [r for r in records if (parsed := parse_date(r.get(date_key, ""))) and parsed.date() >= today - timedelta(days=7)]

def safe_preview(title, records, date_col):
    st.markdown(f"### {title}")
    filtered = filter_last_7_days(records, date_col)
    st.dataframe(pd.DataFrame(filtered)) if filtered else st.write("No records in last 7 days.")

# === SHEETS & HEADERS ===
ufd_headers = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices", "Notes",
    "UncoatedSpool_ID", "Date_Time"
]
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ufd_headers)
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", ["UncoatedSpool_ID", "Type", "C_Length", "Date_Time"])

# === FIBER FORM ===
st.header("📋 Uncoated Fiber Data Entry")
st.info("You can either upload vendor file or fill manually. Auto-prefill works if headers match.")

batch_fiber_id = get_next_id(ufd_sheet, "Batch_Fiber_ID")
st.markdown(f"**Next Batch_Fiber_ID**: `{batch_fiber_id}`")

uncoated_spool_ids = [r["UncoatedSpool_ID"] for r in usid_sheet.get_all_records()]

uploaded_file = st.file_uploader("Upload vendor data (optional, .xlsx or .csv)", type=["csv", "xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)
    st.dataframe(df.head())
else:
    df = pd.DataFrame()

with st.form("Uncoated Fiber Data Form"):
    selected_uncoated_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
    if not df.empty:
        supplier_batch_id = df.iloc[0].get("Tracking number UPS", "")
        outside_diameter_avg = df.iloc[0].get("OD", 0)
        inside_diameter_avg = df.iloc[0].get("ID", 0)
        batch_length = df.iloc[0].get("Batch length (m)", 0)
        shipment_date = df.iloc[0].get("Shipment date", datetime.today())
        shipment_date = parse_date(str(shipment_date)) or datetime.today()
    else:
        supplier_batch_id = st.text_input("Supplier Batch ID")
        outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", min_value=0.0)
        inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", min_value=0.0)
        batch_length = st.number_input("Batch Length (m)", min_value=0.0)
        shipment_date = st.date_input("Shipment Date", datetime.today())

    inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", min_value=0.0)
    outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", min_value=0.0)
    reported_concentricity = st.number_input("Reported Concentricity (%)", min_value=0.0)
    tracking_number = st.text_input("Tracking Number", value=supplier_batch_id)
    fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"])
    average_t_od = st.number_input("Average t/OD", min_value=0.0)
    minimum_t_od = st.number_input("Minimum t/OD", min_value=0.0)
    minimum_wall_thickness = st.number_input("Minimum Wall Thickness (um)", min_value=0.0)
    average_wall_thickness = st.number_input("Average Wall Thickness (um)", min_value=0.0)
    n2_permeance = st.number_input("N2 Permeance (GPU)", min_value=0.0)
    collapse_pressure = st.number_input("Collapse Pressure (psi)", min_value=0.0)
    kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", min_value=0.0)
    kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", min_value=0.0)
    order_on_bobbin = st.number_input("Order on Bobbin", min_value=0)
    number_of_blue_splices = st.number_input("Number of Blue Splices", min_value=0)
    notes = st.text_area("Notes")

    if st.form_submit_button("Submit Fiber Batch"):
        ufd_sheet.append_row([
            batch_fiber_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
            outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
            shipment_date.strftime("%Y-%m-%d"), tracking_number, fiber_source, average_t_od,
            minimum_t_od, minimum_wall_thickness, average_wall_thickness, n2_permeance,
            collapse_pressure, kink_test_2_95, kink_test_2_36, order_on_bobbin,
            number_of_blue_splices, notes, selected_uncoated_spool_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        st.success(f"Submitted Batch_Fiber_ID {batch_fiber_id} successfully!")
