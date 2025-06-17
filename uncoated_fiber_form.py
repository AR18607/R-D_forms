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

# === UNCOATED FIBER FORM ===
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

if 'batch_list' not in st.session_state:
    st.session_state.batch_list = []

if fiber_source == "Syensqo":
    tracking_numbers = sorted(syensqo_df["Tracking number UPS"].dropna().unique())
    selected_tracking = st.selectbox("Select Tracking Number", tracking_numbers)
    matching_rows = syensqo_df[syensqo_df["Tracking number UPS"] == selected_tracking]

    if not matching_rows.empty:
        selected_row = matching_rows.iloc[0]

        batch_fiber_id = get_next_id(ufd_sheet, "Batch_Fiber_ID")
        st.markdown(f"**Next Batch_Fiber_ID:** `{batch_fiber_id}`")

        with st.form("syensqo_entry_form"):
            supplier_batch_id = st.text_input("Supplier Batch ID", value=selected_tracking)
            inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", value=float(selected_row.get("Inside Diameter (um)", 0)))
            inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", value=float(selected_row.get("Inside Diameter (um) SD", 0)))
            outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", value=float(selected_row.get("Outside Diameter (um)", 0)))
            outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", value=float(selected_row.get("Outside Diameter (um) SD", 0)))
            reported_concentricity = st.number_input("Reported Concentricity (%)", value=float(selected_row.get("Reported Concentricity (%)", 0)))
            batch_length = st.number_input("Batch Length (m)", value=float(selected_row.get("Batch Length (m)", 0)))
            shipment_date = st.date_input("Shipment Date", value=datetime.today())
            average_t_od = st.number_input("Average t/OD", value=float(selected_row.get("Average t/OD", 0)))
            minimum_t_od = st.number_input("Minimum t/OD", value=float(selected_row.get("Minimum t/OD", 0)))
            min_wall_thickness = st.number_input("Minimum Wall Thickness (um)", value=float(selected_row.get("Minimum wall thickness (um)", 0)))
            avg_wall_thickness = st.number_input("Average Wall Thickness (um)", value=float(selected_row.get("Average wall thickness (um)", 0)))
            n2_permeance = st.number_input("N2 Permeance (GPU)", value=float(selected_row.get("N2 permeance (GPU)", 0)))
            collapse_pressure = st.number_input("Collapse Pressure (psi)", value=float(selected_row.get("Collapse Pressure (psi)", 0)))
            kink_295 = st.number_input("Kink Test 2.95 (mm)", value=float(selected_row.get("Kink test 2.95 (mm)", 0)))
            kink_236 = st.number_input("Kink Test 2.36 (mm)", value=float(selected_row.get("Kink test 2.36 (mm)", 0)))
            order_bobbin = st.number_input("Order on Bobbin", value=int(float(selected_row.get("Order on bobbin (outside = 1)", 0))))
            blue_splices = st.number_input("Number of Blue Splices", value=int(float(selected_row.get("Number of blue splices", 0))))
            notes = st.text_area("Notes")
            add_btn = st.form_submit_button("➕ Add to Batch List")

        if add_btn:
            row_data = [
                batch_fiber_id, supplier_batch_id, inside_diameter_avg, inside_diameter_stdev,
                outside_diameter_avg, outside_diameter_stdev, reported_concentricity, batch_length,
                shipment_date.strftime("%Y-%m-%d"), selected_tracking, "Syensqo", average_t_od,
                minimum_t_od, min_wall_thickness, avg_wall_thickness, n2_permeance,
                collapse_pressure, kink_295, kink_236, order_bobbin, blue_splices, notes,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
            st.session_state.batch_list.append(row_data)
            st.success(f"Added Batch_Fiber_ID {batch_fiber_id} to the list. Click below to submit all.")

if st.session_state.batch_list:
    st.markdown("### 📝 Batches to be Submitted:")
    st.dataframe(pd.DataFrame(st.session_state.batch_list, columns=ufd_headers))
    if st.button("✅ Submit All Batches"):
        for row in st.session_state.batch_list:
            ufd_sheet.append_row(row)
        st.success(f"✅ {len(st.session_state.batch_list)} batches submitted successfully.")
        st.session_state.batch_list.clear()