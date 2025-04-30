import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Google Sheets Setup ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = 'path_to_your_service_account.json'  # Replace with your service account file path

import json

gcp_service_account = """
{
  "type": "service_account",
  "project_id": "rnd-form-sheets",
  "private_key_id": "b47d625d6fd990cb396b1c559daa3647595d6765",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCTgcNXEKIvxeLn\\nKLfu4ru/I4osM7UOKwa1w1YF/s+ERiLU8sXY2xb589/B8zTxsMonaNbuVLVF6/hS\\nJyZ3Iq6lbi6OWU46ndyhdQvrvinczlOiDGjrg4kLQy73ylhscTz+m8yg2FnFufmC\\ngPDoKH+M1vBFQ+E/mDS19cr0lYiNwCg5QVYw4ASV3EOG8pm4WZ0hHKMR3fTYyShN\\nYgj1rdKcQBXjbbKFXsMqG0uc55Ul/WQCmf5MdK7ltUElkCmGEH6oYLKxqcKUyGHF\\nhRzGFIxQGILuJ1jJxbcWuruHDPkO3h/MKuuwUqN40YmZkH4cV+23FM8hgfJJNx3m\\nnM+10YWpAgMBAAECggEABf+L2vmBLuIkJPRB7oPn0JD4aG292hKj1jZYRCwlciKL\\n/g7VPslB+O4S1kc2ivF+dvXLb6ugJ3S+B1EyPjv50B5X5E/7X2TV+PbSgkacWy9E\\ntV090v3pT7zupwLib553NX9OZegGVoUGgWkO4tHqxeZjpN1qxnRBCHkzRJjkEaeD\\n6X7ym361mx0q8rMfXGuKxNH4myJdqYIiJtiVeP+lB7d4fSE/GQ8mtY2ATkNAKxpa\\nK0HkBVJvzBXqkJXXf+j9rbsBkN2xk7Lg0BE6F/AsqxwToJ7xH4mWn86ZAUrfzhRz\\n/l/YAG948xPRDTamwkuJyF8sBbFCl0UT3qVC8/fXEQKBgQDK+f3kZBtovj+GjLSZ\\ndEeR+bSF6Co0n/HGy05fhZ4fONDpEj2RtzVGqyPzQCgdNBisp5wskK65zMbxnluw\\nRWBvPgELN9iGnmkfMnuUcALzdCfVenSefN1JyYiFLID0Fu9rkufnsdFuQQfmFc7g\\noYdL9ZUD9ISEFy2R21oM1Y6XTQKBgQC6CkB07WXiRW49OvrZZ9BqmlHJfAc/ISJX\\nIrbu7eOCprlo5J4YUprcAhFkGrOEA7Xoq/bgUG4lp1HEMWJh1n6IYcIu7ssj0Eni\\ntjD/b06JdlVHFLx0UpppIgs64QrnxUi0h0c0xA3+svWGmQOcbaBOYmdz3sUcr4YH\\nBwWDdE9RzQKBgQC5mTn1WyxM7Jl92K9TGiZPbnsJbq8ZC5+y3Tg+1BkwB23PkORH\\nl7TZd6gZx3JmsbpWNbTycyGxt3O6f8jrN6TkU1f1AA23mqYY5rplkr7AClhaNezo\\n9tgJnoR88aLAjzBBt0TicZBFNqWYWByg/lKOvHKT+UQq3F7I3kBLOAN4iQKBgBAd\\nhTnbuqCgHQ2Gx2X/vSkO1xjZ+pK4Xw4nPqtxxexyXss8SomW1j1KnJEMUxKTc7WE\\n9+y0auYuGUIieQA6oVlVBookO0qN52iRGat2y9nSe06d+DknUqLaxRhDmDs9dq/U\\nrBFhDklK3UPci1iIkoNXuNhrqq1ycuy26f5aG+jdAoGBALUmLPuK8R2z/l5ZbVMp\\nwAex2x5xpCY7KxqjK9QEPT4ltpSIEO1wcCLpyJu4ywF+ZEK4tX4m83QSnz3jSJ2P\\n+s2lYdzPlH/h9PmN4dZNEe2Ych2krJ6enL4XFTwLdaTBxhzelBxsIMOBRY+Q8lEk\\nGuc9jxGajgMRjNcZ6KDwxDI0\\n-----END PRIVATE KEY-----\\n",
  "client_email": "streamlit-sheets-access@rnd-form-sheets.iam.gserviceaccount.com",
  "client_id": "110606493187856294523",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/streamlit-sheets-access%40rnd-form-sheets.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""

credentials = Credentials.from_service_account_info(json.loads(gcp_service_account), scopes=SCOPES)

client = gspread.authorize(credentials)

# --- Google Sheet URLs ---
MAIN_SHEET_URL = 'https://docs.google.com/spreadsheets/d/your_main_sheet_id'  # Replace with your main sheet URL
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
