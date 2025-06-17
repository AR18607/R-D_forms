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
sheet_url = "https://docs.google.com/spreadsheets/d/1AGZ1g3LeSPtLAKV685snVQeERWXVPF4WlIAV8aAj9o8"
spreadsheet = client.open_by_url(sheet_url)

# === LOAD SYENSQO SHEET SAFELY ===
syensqo_sheet = spreadsheet.worksheet("Sheet1")
raw_data = syensqo_sheet.get_all_values()
headers = [h.strip() for h in raw_data[0]]
data_rows = raw_data[1:]
syensqo_df = pd.DataFrame(data_rows, columns=headers)

# Clean tracking number column
syensqo_df["Tracking number UPS"] = syensqo_df["Tracking number UPS"].astype(str).str.strip()
syensqo_df = syensqo_df[syensqo_df["Tracking number UPS"] != ""]

# Strip all other column values of whitespace
syensqo_df = syensqo_df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)

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

def parse_float(val):
    try:
        val = str(val).replace(",", "").replace("%", "").strip()
        return float(val)
    except:
        return 0.0

def parse_int(val):
    try:
        val = str(val).replace(",", "").replace("%", "").strip()
        return int(float(val))
    except:
        return 0

# === UNCOATED FIBER FORM ===
st.header("Uncoated Fiber Data Entry")
ufd_headers = [
    "Batch_Fiber_ID", "Spool_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices",
    "Notes", "Date_Time"
]
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", ufd_headers)

fiber_source = st.selectbox("Fiber Source", ["EMI", "Syensqo", "Polymem", "Other"])

if 'batch_list' not in st.session_state:
    st.session_state.batch_list = []

if fiber_source == "Syensqo":
    tracking_numbers = sorted(syensqo_df["Tracking number UPS"].dropna().unique())
    selected_tracking = st.selectbox("Select Tracking Number", tracking_numbers)
    matching_rows = syensqo_df[syensqo_df["Tracking number UPS"] == selected_tracking]

    if not matching_rows.empty:
        selected_row = matching_rows.iloc[0]

        with st.form("syensqo_entry_form"):
            batch_fiber_id = st.text_input("Batch Fiber ID (provided by vendor)")
            spool_id = st.text_input("Spool ID")
            supplier_batch_id = st.text_input("Supplier Batch ID", value=selected_tracking)
            inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", value=parse_float(selected_row.get("ID", 0)))
            inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", value=0.0)
            outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", value=parse_float(selected_row.get("OD", 0)))
            outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", value=0.0)
            reported_concentricity = st.number_input("Reported Concentricity (%)", value=0.0)
            batch_length = st.number_input("Batch Length (m)", value=parse_float(selected_row.get("Batch length (m)", 0)))
            shipment_date_val = selected_row.get("Shipment date", "")
            try:
                parsed_date = datetime.strptime(shipment_date_val, "%m/%d/%Y")
            except:
                parsed_date = datetime.today()
                shipment_date = st.date_input("Shipment Date", value=parsed_date)

            average_t_od = st.number_input("Average t/OD", value=0.0)
            minimum_t_od = st.number_input("Minimum t/OD", value=0.0)
            min_wall_thickness = st.number_input("Minimum Wall Thickness (um)", value=0.0)
            avg_wall_thickness = st.number_input("Average Wall Thickness (um)", value=0.0)
            n2_permeance = st.number_input("N2 Permeance (GPU)", value=0.0)
            collapse_pressure = st.number_input("Collapse Pressure (psi)", value=0.0)
            kink_295 = st.number_input("Kink Test 2.95 (mm)", value=0.0)
            kink_236 = st.number_input("Kink Test 2.36 (mm)", value=0.0)
            order_bobbin = st.number_input("Order on Bobbin", value=0)
            blue_splices = st.number_input("Number of Blue Splices", value=0)
            notes = st.text_area("Notes")
            add_btn = st.form_submit_button("➕ Add to Batch List")

            if add_btn and batch_fiber_id and spool_id:
                row_data = [
                    batch_fiber_id, spool_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
                    outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
                    shipment_date.strftime("%Y-%m-%d"), selected_tracking, "Syensqo", average_t_od,
                    minimum_t_od, min_wall_thickness, avg_wall_thickness, n2_permeance,
                    collapse_pressure, kink_295, kink_236, order_bobbin, blue_splices, notes,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
                st.session_state.batch_list.append(row_data)
                st.success(f"Added Batch_Fiber_ID {batch_fiber_id} to the list. Click below to submit all.")
            elif add_btn:
                st.warning("Please enter both Batch_Fiber_ID and Spool_ID before adding to the list.")

if st.session_state.batch_list:
    st.markdown("### 📝 Batches to be Submitted:")
    st.dataframe(pd.DataFrame(st.session_state.batch_list, columns=ufd_headers))
    if st.button("✅ Submit All Batches"):
        for row in st.session_state.batch_list:
            ufd_sheet.append_row(row, value_input_option="USER_ENTERED")
        st.success(f"✅ {len(st.session_state.batch_list)} batches submitted successfully.")
        st.session_state.batch_list.clear()

# ------------------ As Received UnCoatedSpools Tbl ------------------ #
st.header("As Received UnCoatedSpools Entry")

ar_headers = ["Received_Spool_PK", "UncoatedSpool_ID", "Batch_Fiber_ID", "Notes", "Date_Time"]
ar_sheet = get_or_create_worksheet(spreadsheet, "As Received UnCoatedSpools Tbl", ar_headers)

# Fetch existing UncoatedSpool_IDs and Batch_Fiber_IDs for dropdowns
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", ["UncoatedSpool_ID", "Date_Time"])

uncoated_spool_ids = [record["UncoatedSpool_ID"] for record in usid_sheet.get_all_records() if record["UncoatedSpool_ID"]]
batch_fiber_ids = [record["Batch_Fiber_ID"] for record in ufd_sheet.get_all_records() if record["Batch_Fiber_ID"]]

if uncoated_spool_ids and batch_fiber_ids:
    with st.form("As Received UnCoatedSpools Form"):
        selected_uncoated_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
        selected_batch_fiber_id = st.selectbox("Batch Fiber ID", batch_fiber_ids)
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Submit")
        if submitted:
            try:
                received_spool_pk = get_next_id(ar_sheet, "Received_Spool_PK")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ar_sheet.append_row([received_spool_pk, selected_uncoated_spool_id, selected_batch_fiber_id, notes, timestamp])
                st.success(f"As Received UnCoatedSpool with PK {received_spool_pk} submitted successfully!")
            except Exception as e:
                st.error(f"❌ Failed to submit: {e}")
else:
    st.warning("⚠️ Please ensure both UncoatedSpool IDs and Batch Fiber IDs are available before submitting.")

# ------------------ Combined Spools Tbl ------------------ #
st.header("Combined Spools Entry")

cs_headers = ["Combined_SpoolsPK", "UncoatedSpool_ID", "Received_Spool_PK", "Date_Time"]
cs_sheet = get_or_create_worksheet(spreadsheet, "Combined Spools Tbl", cs_headers)

# Fetch existing Received_Spool_PKs for dropdown
received_spool_pks = [record["Received_Spool_PK"] for record in ar_sheet.get_all_records() if record["Received_Spool_PK"]]

if uncoated_spool_ids and received_spool_pks:
    with st.form("Combined Spools Form"):
        selected_uncoated_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
        selected_received_spool_pk = st.selectbox("Received Spool PK", received_spool_pks)

        submitted = st.form_submit_button("Submit")
        if submitted:
            try:
                combined_spools_pk = get_next_id(cs_sheet, "Combined_SpoolsPK")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cs_sheet.append_row([combined_spools_pk, selected_uncoated_spool_id, selected_received_spool_pk, timestamp])
                st.success(f"Combined Spool with PK {combined_spools_pk} submitted successfully!")
            except Exception as e:
                st.error(f"❌ Failed to submit: {e}")
else:
    st.warning("⚠️ Please ensure both UncoatedSpool IDs and Received Spool PKs are available before submitting.")

# ------------------ Ardent Fiber Dimension QC Tbl ------------------ #
st.header("Ardent Fiber Dimension QC Entry")

qc_headers = [
    "Ardent_QC_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Ardent_QC_Inside_Diameter",
    "Ardent_QC_Outside_Diameter", "Measured_Concentricity", "Wall_Thickness",
    "Operator_Initials", "Notes", "Date_Time", "Inside_Circularity", "Outside_Circularity"
]
qc_sheet = get_or_create_worksheet(spreadsheet, "Ardent Fiber Dimension QC Tbl", qc_headers)

# Only allow form if dropdowns are valid
if batch_fiber_ids and uncoated_spool_ids:
    with st.form("Ardent Fiber Dimension QC Form"):
        selected_batch_fiber_id = st.selectbox("Batch Fiber ID", batch_fiber_ids)
        selected_uncoated_spool_id = st.selectbox("UncoatedSpool ID", uncoated_spool_ids)
        ardent_qc_inside_diameter = st.number_input("Ardent QC Inside Diameter (um)", min_value=0.0)
        ardent_qc_outside_diameter = st.number_input("Ardent QC Outside Diameter (um)", min_value=0.0)
        measured_concentricity = st.number_input("Measured Concentricity (%)", min_value=0.0)
        wall_thickness = st.number_input("Wall Thickness (um)", min_value=0.0)
        operator_initials = st.text_input("Operator Initials")
        notes = st.text_area("Notes")
        date_time = st.date_input("Date", value=datetime.today())
        inside_circularity = st.number_input("Inside Circularity", min_value=0.0)
        outside_circularity = st.number_input("Outside Circularity", min_value=0.0)

        submitted = st.form_submit_button("Submit")
        if submitted:
            try:
                ardent_qc_id = get_next_id(qc_sheet, "Ardent_QC_ID")
                timestamp = date_time.strftime("%Y-%m-%d %H:%M:%S")
                qc_sheet.append_row([
                    ardent_qc_id, selected_batch_fiber_id, selected_uncoated_spool_id,
                    ardent_qc_inside_diameter, ardent_qc_outside_diameter, measured_concentricity,
                    wall_thickness, operator_initials, notes, timestamp,
                    inside_circularity, outside_circularity
                ])
                st.success(f"Ardent Fiber QC Entry with ID {ardent_qc_id} submitted successfully!")
            except Exception as e:
                st.error(f"❌ Failed to submit QC entry: {e}")
else:
    st.warning("⚠️ Please ensure Batch Fiber IDs and UncoatedSpool IDs are populated before entering QC data.")


# ------------------ 7-DAYS DATA PREVIEW FOR ALL TABLES ------------------
st.markdown("## 📅 Last 7 Days Data Preview")

def parse_date(date_str):
    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except Exception:
            continue
    return None

def filter_last_7_days(records, date_key):
    today = datetime.today()
    filtered_records = []
    for record in records:
        date_str = record.get(date_key, "").strip()
        parsed = parse_date(date_str)
        if parsed and parsed.date() >= (today - timedelta(days=7)).date():
            filtered_records.append(record)
    return filtered_records

def safe_preview(title, records, date_col):
    st.markdown(f"### {title}")
    filtered = filter_last_7_days(records, date_col)
    if filtered:
        st.dataframe(pd.DataFrame(filtered))
    else:
        st.write("No records in the last 7 days.")

# Preview all tables
safe_preview("🧪 Uncoated Fiber Data", ufd_sheet.get_all_records(), "Date_Time")
safe_preview("🧵 UnCoatedSpool ID", usid_sheet.get_all_records(), "Date_Time")
safe_preview("📦 As Received UncoatedSpools", ar_sheet.get_all_records(), "Date_Time")
safe_preview("🔗 Combined Spools", cs_sheet.get_all_records(), "Date_Time")
safe_preview("🧪 Ardent Fiber Dimension QC", qc_sheet.get_all_records(), "Date_Time")




