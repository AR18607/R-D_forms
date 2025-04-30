import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from google.oauth2 import service_account
import json

# --- Load credentials from Streamlit secrets ---
service_account_info = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(credentials)

# --- Google Sheet URLs ---
MAIN_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1uPdUWiiwMdJCYJaxZ5TneFa9h6tbSrs327BVLT5GVPY'
SYENSQO_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1y1pX5ZursJllWZCK-SFt-FTsDSrwjYObmdaA50eH0U8'

# --- Worksheet Names ---
UNCOATED_FIBER_SHEET = 'Uncoated_Fiber_Data_Tbl'

# --- Load Worksheets ---
main_sheet = client.open_by_url(MAIN_SHEET_URL)
syensqo_sheet = client.open_by_url(SYENSQO_SHEET_URL)
syensqo_ws = syensqo_sheet.sheet1  # Assuming data is in the first sheet

# --- Load Syensqo Data ---
syensqo_data = syensqo_ws.get_all_records()
syensqo_df = pd.DataFrame(syensqo_data)

# --- Streamlit Form ---
st.title("Uncoated Fiber Data Entry Form")

with st.form("uncoated_fiber_form"):
    supplier_batch_id = st.text_input("Supplier Batch ID")
    fiber_source = st.selectbox("Fiber Source", ["Syensqo", "EMI", "Polymem", "Other"])
    shipment_date = st.date_input("Shipment Date", datetime.today())
    tracking_number = st.text_input("Tracking Number")
    notes = st.text_area("Notes")

    # Autofill for Syensqo
    if fiber_source == "Syensqo":
        matching_rows = syensqo_df[syensqo_df['Supplier Batch ID'] == supplier_batch_id]
        if not matching_rows.empty:
            row = matching_rows.iloc[0]
            inside_diameter_avg = row.get('Inside Diameter (um) avg', '')
            inside_diameter_stdev = row.get('Inside Diameter (um) StDev', '')
            outside_diameter_avg = row.get('Outside Diameter (um) Avg', '')
            outside_diameter_stdev = row.get('Outside Diameter (um) StDev', '')
            reported_concentricity = row.get('Reported Concentricity (%)', '')
            batch_length = row.get('Batch Length (m)', '')
            average_t_od = row.get('Average t/OD', '')
            minimum_t_od = row.get('Minimum t/OD', '')
            minimum_wall_thickness = row.get('Minimum wall thickness (um)', '')
            average_wall_thickness = row.get('Average wall thickness (um)', '')
            n2_permeance = row.get('N2 permeance (GPU)', '')
            collapse_pressure = row.get('Collapse Pressure (psi)', '')
            kink_test_2_95 = row.get('Kink test 2.95 (mm)', '')
            kink_test_2_36 = row.get('Kink test 2.36 (mm)', '')
            order_on_bobbin = row.get('Order on bobbin (outside = 1)', '')
            number_of_blue_splices = row.get('Number of blue splices', '')
        else:
            st.warning("No matching Syensqo data found for the provided Supplier Batch ID.")
            inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", min_value=0)
            inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", min_value=0)
            outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", min_value=0)
            outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", min_value=0)
            reported_concentricity = st.number_input("Reported Concentricity (%)", min_value=0)
            batch_length = st.number_input("Batch Length (m)", min_value=0)
            average_t_od = st.number_input("Average t/OD", min_value=0.0, format="%.2f")
            minimum_t_od = st.number_input("Minimum t/OD", min_value=0.0, format="%.2f")
            minimum_wall_thickness = st.number_input("Minimum Wall Thickness (um)", min_value=0)
            average_wall_thickness = st.number_input("Average Wall Thickness (um)", min_value=0)
            n2_permeance = st.number_input("N2 Permeance (GPU)", min_value=0)
            collapse_pressure = st.number_input("Collapse Pressure (psi)", min_value=0)
            kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", min_value=0.0, format="%.2f")
            kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", min_value=0.0, format="%.2f")
            order_on_bobbin = st.number_input("Order on Bobbin", min_value=0)
            number_of_blue_splices = st.number_input("Number of Blue Splices", min_value=0)
    else:
        inside_diameter_avg = st.number_input("Inside Diameter Avg (um)", min_value=0)
        inside_diameter_stdev = st.number_input("Inside Diameter StDev (um)", min_value=0)
        outside_diameter_avg = st.number_input("Outside Diameter Avg (um)", min_value=0)
        outside_diameter_stdev = st.number_input("Outside Diameter StDev (um)", min_value=0)
        reported_concentricity = st.number_input("Reported Concentricity (%)", min_value=0)
        batch_length = st.number_input("Batch Length (m)", min_value=0)
        average_t_od = st.number_input("Average t/OD", min_value=0.0, format="%.2f")
        minimum_t_od = st.number_input("Minimum t/OD", min_value=0.0, format="%.2f")
        minimum_wall_thickness = st.number_input("Minimum Wall Thickness (um)", min_value=0)
        average_wall_thickness = st.number_input("Average Wall Thickness (um)", min_value=0)
        n2_permeance = st.number_input("N2 Permeance (GPU)", min_value=0)
        collapse_pressure = st.number_input("Collapse Pressure (psi)", min_value=0)
        kink_test_2_95 = st.number_input("Kink Test 2.95 (mm)", min_value=0.0, format="%.2f")
        kink_test_2_36 = st.number_input("Kink Test 2.36 (mm)", min_value=0.0, format="%.2f")
        order_on_bobbin = st.number_input("Order on Bobbin", min_value=0)
        number_of_blue_splices = st.number_input("Number of Blue Splices", min_value=0)

    submitted = st.form_submit_button("Submit")

    if submitted:
        # Prepare data row
        data_row = [
            supplier_batch_id,
            inside_diameter_avg,
            inside_diameter_stdev,
            outside_diameter_avg,
            outside_diameter_stdev,
            reported_concentricity,
            batch_length,
            shipment_date.strftime("%Y-%m-%d"),
            tracking_number,
            fiber_source,
            average_t_od,
            minimum_t_od,
            minimum_wall_thickness,
            average_wall_thickness,
            n2_permeance,
            collapse_pressure,
            kink_test_2_95,
            kink_test_2_36,
            order_on_bobbin,
            number_of_blue_splices,
            notes
        ]

        # Access or create worksheet
        try:
            worksheet = main_sheet.worksheet(UNCOATED_FIBER_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = main_sheet.add_worksheet(title=UNCOATED_FIBER_SHEET, rows="1000", cols="20")
            headers = [
                "Supplier Batch ID",
                "Inside Diameter Avg (um)",
                "Inside Diameter StDev (um)",
                "Outside Diameter Avg (um)",
                "Outside Diameter StDev (um)",
                "Reported Concentricity (%)",
                "Batch Length (m)",
                "Shipment Date",
                "Tracking Number",
                "Fiber Source",
                "Average t/OD",
                "Minimum t/OD",
                "Minimum Wall Thickness (um)",
                "Average Wall Thickness (um)",
                "N2 Permeance (GPU)",
                "Collapse Pressure (psi)",
                "Kink Test 2.95 (mm)",
                "Kink Test 2.36 (mm)",
                "Order on Bobbin",
                "Number of Blue Splices",
                "Notes"
            ]
            worksheet.append_row(headers)

        # Append data row
        worksheet.append_row(data_row)
        st.success("Data submitted successfully!")
