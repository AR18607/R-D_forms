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

# Clean fiber number column
syensqo_df["Fiber"] = syensqo_df["Fiber"].astype(str).str.strip()
syensqo_df = syensqo_df[syensqo_df["Fiber"] != ""]

# Clean tracking number column
syensqo_df["Tracking number UPS"] = syensqo_df["Tracking number UPS"].astype(str).str.strip()
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
    syensqo_fibers = sorted(syensqo_df["Fiber"].dropna().unique())
    selected_fiber = st.selectbox("Select Fiber", syensqo_fibers)
    matching_rows = syensqo_df[syensqo_df["Fiber"] == selected_fiber]
    if not matching_rows.empty:
        selected_row = matching_rows.iloc[0]

        with st.form("syensqo_entry_form"):
            batch_fiber_id = st.text_input("Batch Fiber ID (provided by vendor)", value=selected_row.get("Fiber", ""))
            spool_id = st.text_input("Spool ID")
            supplier_batch_id = st.text_input("Supplier Batch ID", value=selected_row.get("Fiber", ""))
            inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", value=parse_float(selected_row.get("ID", 0)))
            inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", value=0.0)
            outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", value=parse_float(selected_row.get("OD", 0)))
            outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", value=0.0)
            reported_concentricity = st.number_input("Reported Concentricity (%)", value=0.0)
            batch_length = st.number_input("Batch Length (m)", value=parse_float(selected_row.get("Batch length (m)", 0)))
            shipment_date_val = selected_row.get("Shipment date", "")
            try:
                parsed_date = datetime.strptime(str(shipment_date_val), "%m/%d/%Y")
            except:
                parsed_date = datetime.today()
            shipment_date = st.date_input("Shipment Date", value=parsed_date)
            tracking_number = st.text_input("Tracking Number", value=selected_row.get("Tracking number UPS", ""))
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
            if add_btn:
                if batch_fiber_id and spool_id:
                    row_data = [
                        batch_fiber_id, spool_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
                        outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
                        shipment_date.strftime("%Y-%m-%d"), tracking_number, "Syensqo",
                        average_t_od, minimum_t_od, min_wall_thickness, avg_wall_thickness, n2_permeance,
                        collapse_pressure, kink_295, kink_236, order_bobbin, blue_splices, notes,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    st.session_state.batch_list.append(row_data)
                    st.success(f"Added Batch_Fiber_ID {batch_fiber_id} to the list. Click below to submit all.")
                else:
                    st.warning("Please enter both Batch_Fiber_ID and Spool_ID before adding to the list.")
else:
    # ALL FIELDS MANUAL ENTRY FOR OTHER VENDORS (EMI, Polymem, Other)
    with st.form("other_vendor_entry_form"):
        batch_fiber_id = st.text_input("Batch Fiber ID (provided by vendor)")
        spool_id = st.text_input("Spool ID")
        supplier_batch_id = st.text_input("Supplier Batch ID")
        inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", value=0.0)
        inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", value=0.0)
        outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", value=0.0)
        outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", value=0.0)
        reported_concentricity = st.number_input("Reported Concentricity (%)", value=0.0)
        batch_length = st.number_input("Batch Length (m)", value=0.0)
        shipment_date = st.date_input("Shipment Date", value=datetime.today())
        tracking_number = st.text_input("Tracking Number")
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
        if add_btn:
            if batch_fiber_id and spool_id:
                row_data = [
                    batch_fiber_id, spool_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
                    outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
                    shipment_date.strftime("%Y-%m-%d"), tracking_number, fiber_source,
                    average_t_od, minimum_t_od, min_wall_thickness, avg_wall_thickness, n2_permeance,
                    collapse_pressure, kink_295, kink_236, order_bobbin, blue_splices, notes,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
                st.session_state.batch_list.append(row_data)
                st.success(f"Added Batch_Fiber_ID {batch_fiber_id} to the list. Click below to submit all.")
            else:
                st.warning("Please enter both Batch_Fiber_ID and Spool_ID before adding to the list.")

if st.session_state.batch_list:
    st.markdown("### 📝 Batches to be Submitted:")
    st.dataframe(pd.DataFrame(st.session_state.batch_list, columns=ufd_headers))
    if st.button("✅ Submit All Batches"):
        for row in st.session_state.batch_list:
            ufd_sheet.append_row(row, value_input_option="USER_ENTERED")
        st.success(f"✅ {len(st.session_state.batch_list)} batches submitted successfully.")
        st.session_state.batch_list.clear()

# The rest of your code for As Received, Combined Spools, QC, and Preview stays the same.
# ========== As Received UnCoatedSpools Tbl ==========
ar_headers = ["Received_Spool_PK", "UncoatedSpool_ID", "Batch_Fiber_ID", "Notes", "Date_Time"]
ar_sheet = get_or_create_worksheet(spreadsheet, "As Received UnCoatedSpools Tbl", ar_headers)

st.header("Manual Entry: As Received UnCoatedSpools Table")
with st.form("ar_entry_form_manual"):
    received_spool_pk_manual = st.text_input("Received Spool PK (manual)")
    uncoated_spool_id_ar_manual = st.text_input("UncoatedSpool ID (manual, AR)")
    batch_fiber_id_ar_manual = st.text_input("Batch Fiber ID (manual, AR)")
    notes_ar_manual = st.text_area("Notes (manual, AR)")
    ar_date_manual = st.date_input("Date (manual, AR)", value=datetime.today(), key="ar_manual")
    submit_ar_manual = st.form_submit_button("Add As Received Spool (Manual)")
    if submit_ar_manual:
        if received_spool_pk_manual and uncoated_spool_id_ar_manual and batch_fiber_id_ar_manual:
            ar_sheet.append_row([
                received_spool_pk_manual,
                uncoated_spool_id_ar_manual,
                batch_fiber_id_ar_manual,
                notes_ar_manual,
                ar_date_manual.strftime("%Y-%m-%d %H:%M:%S")
            ])
            st.success(f"Added As Received Spool PK {received_spool_pk_manual}")
        else:
            st.warning("Please fill all fields for As Received entry.")

# ========== Combined Spools Tbl ==========
cs_headers = ["Combined_SpoolsPK", "UncoatedSpool_ID", "Received_Spool_PK", "Date_Time"]
cs_sheet = get_or_create_worksheet(spreadsheet, "Combined Spools Tbl", cs_headers)

st.header("Manual Entry: Combined Spools Table")
with st.form("cs_entry_form_manual"):
    combined_spools_pk_manual = st.text_input("Combined Spools PK (manual)")
    uncoated_spool_id_cs_manual = st.text_input("UncoatedSpool ID (manual, Combined)")
    received_spool_pk_cs_manual = st.text_input("Received Spool PK (manual, Combined)")
    cs_date_manual = st.date_input("Date (manual, Combined)", value=datetime.today(), key="cs_manual")
    submit_cs_manual = st.form_submit_button("Add Combined Spools (Manual)")
    if submit_cs_manual:
        if combined_spools_pk_manual and uncoated_spool_id_cs_manual and received_spool_pk_cs_manual:
            cs_sheet.append_row([
                combined_spools_pk_manual,
                uncoated_spool_id_cs_manual,
                received_spool_pk_cs_manual,
                cs_date_manual.strftime("%Y-%m-%d %H:%M:%S")
            ])
            st.success(f"Added Combined Spools PK {combined_spools_pk_manual}")
        else:
            st.warning("Please fill all fields for Combined Spools entry.")

# ========== Ardent Fiber Dimension QC Tbl ==========
qc_headers = [
    "Ardent_QC_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Ardent_QC_Inside_Diameter",
    "Ardent_QC_Outside_Diameter", "Measured_Concentricity", "Wall_Thickness",
    "Operator_Initials", "Notes", "Date_Time", "Inside_Circularity", "Outside_Circularity"
]
qc_sheet = get_or_create_worksheet(spreadsheet, "Ardent Fiber Dimension QC Tbl", qc_headers)

st.header("Manual Entry: Ardent Fiber Dimension QC Table")
with st.form("qc_entry_form_manual"):
    ardent_qc_id_manual = st.text_input("Ardent QC ID (manual)")
    batch_fiber_id_qc_manual = st.text_input("Batch Fiber ID (manual, QC)")
    uncoated_spool_id_qc_manual = st.text_input("UncoatedSpool ID (manual, QC)")
    ardent_qc_inside_diameter_manual = st.number_input("Ardent QC Inside Diameter (um) (manual)", min_value=0.0, key="qc_in_manual")
    ardent_qc_outside_diameter_manual = st.number_input("Ardent QC Outside Diameter (um) (manual)", min_value=0.0, key="qc_out_manual")
    measured_concentricity_manual = st.number_input("Measured Concentricity (%) (manual)", min_value=0.0, key="qc_conc_manual")
    wall_thickness_manual = st.number_input("Wall Thickness (um) (manual)", min_value=0.0, key="qc_wall_manual")
    operator_initials_manual = st.text_input("Operator Initials (manual, QC)")
    notes_qc_manual = st.text_area("Notes (manual, QC)")
    qc_date_manual = st.date_input("Date (manual, QC)", value=datetime.today(), key="qc_manual")
    inside_circularity_manual = st.number_input("Inside Circularity (manual)", min_value=0.0, key="qc_ic_manual")
    outside_circularity_manual = st.number_input("Outside Circularity (manual)", min_value=0.0, key="qc_oc_manual")
    submit_qc_manual = st.form_submit_button("Add Ardent QC Entry (Manual)")
    if submit_qc_manual:
        if ardent_qc_id_manual and batch_fiber_id_qc_manual and uncoated_spool_id_qc_manual:
            qc_sheet.append_row([
                ardent_qc_id_manual,
                batch_fiber_id_qc_manual,
                uncoated_spool_id_qc_manual,
                ardent_qc_inside_diameter_manual,
                ardent_qc_outside_diameter_manual,
                measured_concentricity_manual,
                wall_thickness_manual,
                operator_initials_manual,
                notes_qc_manual,
                qc_date_manual.strftime("%Y-%m-%d %H:%M:%S"),
                inside_circularity_manual,
                outside_circularity_manual
            ])
            st.success(f"Added Ardent QC Entry {ardent_qc_id_manual}")
        else:
            st.warning("Please fill all required QC fields.")



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

def safe_preview(title, records, headers):
    st.markdown(f"### {title}")
    df = pd.DataFrame(records, columns=headers)
    st.dataframe(df)  # Always shows headers even if no rows
    if df.empty:
        st.markdown('<div style="color: #888; font-size: 16px;">No records in the last 7 days.</div>', unsafe_allow_html=True)

safe_preview("🧪 Uncoated Fiber Data", filter_last_7_days(ufd_sheet.get_all_records(), "Date_Time"), ufd_headers)
safe_preview("🧵 UnCoatedSpool ID", filter_last_7_days(usid_sheet.get_all_records(), "Date_Time"), ["UncoatedSpool_ID", "Date_Time"])
safe_preview("📦 As Received UncoatedSpools", filter_last_7_days(ar_sheet.get_all_records(), "Date_Time"), ar_headers)
safe_preview("🔗 Combined Spools", filter_last_7_days(cs_sheet.get_all_records(), "Date_Time"), cs_headers)
safe_preview("🧪 Ardent Fiber Dimension QC", filter_last_7_days(qc_sheet.get_all_records(), "Date_Time"), qc_headers)
