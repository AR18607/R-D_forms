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
syensqo_sheet = client.open_by_url(sheet_url).worksheet("Sheet1")
raw_data = syensqo_sheet.get_all_values()
headers = raw_data[0]
data_rows = raw_data[1:]
syensqo_df = pd.DataFrame(data_rows, columns=headers)

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
    syensqo_df["Tracking number UPS"] = syensqo_df["Tracking number UPS"].astype(str).str.strip()
    tracking_numbers = syensqo_df["Tracking number UPS"].dropna().unique().tolist()
    selected_tracking = st.selectbox("Select Tracking Number", tracking_numbers)

if selected_tracking:
    matching_rows = syensqo_df[syensqo_df["Tracking number UPS"].astype(str).str.strip() == selected_tracking]
    if not matching_rows.empty:
        selected_row = matching_rows.iloc[0]


    batch_fiber_id = get_next_id(ufd_sheet, "Batch_Fiber_ID")
    st.markdown(f"**Next Batch_Fiber_ID:** `{batch_fiber_id}`")

    with st.form("syensqo_entry_form"):
        notes = st.text_area("Notes")
        add_btn = st.form_submit_button("➕ Add to Batch List")

    if add_btn:
        row_data = [
            batch_fiber_id,
            selected_row.get("Supplier batch ID", ""),
            selected_row.get("Inside Diameter (um) avg", 0),
            selected_row.get("Inside Diameter (um) StDev", 0),
            selected_row.get("Outside Diameter (um) Avg", 0),
            selected_row.get("Outside Diameter (um) StDev", 0),
            selected_row.get("Reported Concentricity (%)", 0),
            selected_row.get("Batch Length (m)", 0),
            selected_row.get("Shipment Date", datetime.today().strftime("%Y-%m-%d")),
            selected_row.get("Tracking number", ""),
            "Syensqo",
            selected_row.get("Average t/OD", 0.0),
            selected_row.get("Minimum t/OD", 0.0),
            selected_row.get("Minimum wall thickness (um)", 0),
            selected_row.get("Average wall thickness (um)", 0),
            selected_row.get("N2 permeance (GPU)", 0),
            selected_row.get("Collapse Pressure (psi)", 0),
            selected_row.get("Kink test 2.95 (mm)", 0.0),
            selected_row.get("Kink test 2.36 (mm)", 0.0),
            selected_row.get("Order on bobbin (outside = 1)", 0),
            selected_row.get("Number of blue splices", 0),
            notes,
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
