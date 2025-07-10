import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# === GOOGLE SHEET SETUP ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
sheet_url = "https://docs.google.com/spreadsheets/d/1AGZ1g3LeSPtLAKV685snVQeERWXVPF4WlIAV8aAj9o8"
spreadsheet = client.open_by_url(sheet_url)

# === HEADERS (MATCH YOUR GOOGLE SHEET TABLE) ===
UFD_HEADERS = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices", "Notes", "Date_Time"
]

# === LOAD SYENSQO SHEET: MANUAL HEADER ASSIGNMENT ===
try:
    syensqo_sheet = spreadsheet.worksheet("Syensqo")
except Exception:
    syensqo_sheet = None

syensqo_df = pd.DataFrame()
if syensqo_sheet:
    syensqo_raw = syensqo_sheet.get_all_values()
    if len(syensqo_raw) > 2:
        syensqo_headers = [
            "Fiber", "Shipment date", "Tracking number UPS", "Batch length (m)", "OD", "SD",
            "ID", "SD_ID", "Thickness (µm)", "Thickness/OD", "minimum thickness/OD",
            "Concentricity (%)", "GPU (N2)", "Collapse pressure (PSI)",
            "Kink test 2.95 inches (mm)", "Kink test 2.36 inches (mm)",
            "Bobbin number", "Order (coating)", "Blue Splicings number", "Surface (m^2)"
        ]
        syensqo_data = syensqo_raw[2:]  # Data starts from 3rd row
        trimmed_data = [row[:len(syensqo_headers)] for row in syensqo_data]
        syensqo_df = pd.DataFrame(trimmed_data, columns=syensqo_headers)
        syensqo_df = syensqo_df.loc[~(syensqo_df == '').all(axis=1)]
        st.write("DEBUG: Syensqo column headers:", list(syensqo_df.columns))
        if not syensqo_df.empty:
            st.write("DEBUG: First data row dict:", syensqo_df.iloc[0].to_dict())
    else:
        syensqo_df = pd.DataFrame()

def safe_float(val):
    try:
        val = str(val).strip().replace(",", "")
        if val.lower() == "no kink" or val == "":
            return 0.0
        return float(val)
    except Exception:
        return 0.0

def safe_int(val):
    try:
        val = str(val).strip().replace(",", "")
        if val == "":
            return 0
        return int(float(val))
    except Exception:
        return 0

def safe_text(val):
    return str(val).strip() if val is not None else ""

def parse_date(val):
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except Exception:
            continue
    return datetime.today().date()

# === UFD SHEET PREP ===
try:
    ufd_sheet = spreadsheet.worksheet("Uncoated Fiber Data Tbl")
except Exception:
    st.error("Could not find 'Uncoated Fiber Data Tbl' worksheet!")
    st.stop()
ufd_ws_headers = ufd_sheet.row_values(1)
if ufd_ws_headers != UFD_HEADERS:
    ufd_sheet.resize(rows=1)
    ufd_sheet.insert_row(UFD_HEADERS, 1)

# === STREAMLIT FORM ===
st.header("Uncoated Fiber Data Entry")
fiber_source_options = ["Syensqo", "EMI", "Polymem", "other"]
fiber_source = st.selectbox("Fiber Source", fiber_source_options, key="fiber_source")

form_values = {h: "" for h in UFD_HEADERS}
form_values["Fiber_Source"] = fiber_source
form_values["Supplier_Batch_ID"] = st.text_input("Supplier batch ID", key="Supplier_Batch_ID")

if fiber_source == "Syensqo" and not syensqo_df.empty:
    syensqo_fiber_ids = sorted(syensqo_df["Fiber"].dropna().unique())
    selected_fiber = st.selectbox("Batch Fiber ID (from Syensqo sheet)", syensqo_fiber_ids, key="Batch_Fiber_ID")
    syensqo_row = syensqo_df[syensqo_df["Fiber"] == selected_fiber].iloc[0]

    # --- MAPPING: edit the lines below as needed for new/missing fields ---
    form_values["Batch_Fiber_ID"] = safe_text(syensqo_row.get("Fiber", ""))
    form_values["Inside_Diameter_Avg"] = st.number_input(
        "Inside Diameter (um) avg", value=safe_float(syensqo_row.get("ID", 0)), key="Inside_Diameter_Avg"
    )
    form_values["Inside_Diameter_StDev"] = st.number_input(
        "Inside Diameter (um) StDev", value=safe_float(syensqo_row.get("SD_ID", 0)), key="Inside_Diameter_StDev"
    )
    form_values["Outside_Diameter_Avg"] = st.number_input(
        "Outside Diameter (um) Avg", value=safe_float(syensqo_row.get("OD", 0)), key="Outside_Diameter_Avg"
    )
    form_values["Outside_Diameter_StDev"] = st.number_input(
        "Outside Diameter (um) StDev", value=safe_float(syensqo_row.get("SD", 0)), key="Outside_Diameter_StDev"
    )
    form_values["Reported_Concentricity"] = st.number_input(
        "Reported Concentricity (%)", value=safe_float(syensqo_row.get("Concentricity (%)", 0)), key="Reported_Concentricity"
    )
    form_values["Batch_Length"] = st.number_input(
        "Batch Length (m)", value=safe_float(syensqo_row.get("Batch length (m)", 0)), key="Batch_Length"
    )
    form_values["Shipment_Date"] = st.date_input(
        "Shipment Date", value=parse_date(syensqo_row.get("Shipment date", "")), key="Shipment_Date"
    )
    form_values["Tracking_Number"] = st.text_input(
        "Tracking number", value=safe_text(syensqo_row.get("Tracking number UPS", "")), key="Tracking_Number"
    )
    form_values["Average_t_OD"] = st.number_input(
        "Average t/OD", value=safe_float(syensqo_row.get("Thickness/OD", 0)), key="Average_t_OD"
    )
    form_values["Minimum_t_OD"] = st.number_input(
        "Minimum t/OD", value=safe_float(syensqo_row.get("minimum thickness/OD", 0)), key="Minimum_t_OD"
    )
    form_values["Minimum_Wall_Thickness"] = st.number_input(
        "Minimum wall thickness (um)", value=safe_float(syensqo_row.get("Thickness (µm)", 0)), key="Minimum_Wall_Thickness"
    )
    form_values["Average_Wall_Thickness"] = st.number_input(
        "Average wall thickness (um)", value=0.0, key="Average_Wall_Thickness"
    )
    form_values["N2_Permeance"] = st.number_input(
        "N2 permeance (GPU)", value=safe_float(syensqo_row.get("GPU (N2)", 0)), key="N2_Permeance"
    )
    form_values["Collapse_Pressure"] = st.number_input(
        "Collapse Pressure (psi)", value=safe_float(syensqo_row.get("Collapse pressure (PSI)", 0)), key="Collapse_Pressure"
    )
    form_values["Kink_Test_2_95"] = st.number_input(
        "Kink test 2.95 (mm)", value=safe_float(syensqo_row.get("Kink test 2.95 inches (mm)", "")), key="Kink_Test_2_95"
    )
    form_values["Kink_Test_2_36"] = st.number_input(
        "Kink test 2.36 (mm)", value=safe_float(syensqo_row.get("Kink test 2.36 inches (mm)", "")), key="Kink_Test_2_36"
    )
    form_values["Order_On_Bobbin"] = st.number_input(
        "Order on bobbin (outside = 1)", value=safe_int(syensqo_row.get("Bobbin number", 1)), key="Order_On_Bobbin"
    )
    form_values["Number_Of_Blue_Splices"] = st.number_input(
        "Number of blue splices", value=safe_int(syensqo_row.get("Blue Splicings number", 0)), key="Number_Of_Blue_Splices"
    )
    form_values["Notes"] = st.text_area("Notes", value="", key="Notes")

else:
    # --- For EMI, Polymem, Other: All manual input ---
    form_values["Batch_Fiber_ID"] = st.text_input("Batch Fiber ID", key="Batch_Fiber_ID")
    form_values["Inside_Diameter_Avg"] = st.number_input("Inside Diameter (um) avg", value=0, key="Inside_Diameter_Avg")
    form_values["Inside_Diameter_StDev"] = st.number_input("Inside Diameter (um) StDev", value=0, key="Inside_Diameter_StDev")
    form_values["Outside_Diameter_Avg"] = st.number_input("Outside Diameter (um) Avg", value=0, key="Outside_Diameter_Avg")
    form_values["Outside_Diameter_StDev"] = st.number_input("Outside Diameter (um) StDev", value=0, key="Outside_Diameter_StDev")
    form_values["Reported_Concentricity"] = st.number_input("Reported Concentricity (%)", value=0, key="Reported_Concentricity")
    form_values["Batch_Length"] = st.number_input("Batch Length (m)", value=0, key="Batch_Length")
    form_values["Shipment_Date"] = st.date_input("Shipment Date", key="Shipment_Date")
    form_values["Tracking_Number"] = st.text_input("Tracking number", key="Tracking_Number")
    form_values["Average_t_OD"] = st.number_input("Average t/OD", value=0.0, key="Average_t_OD")
    form_values["Minimum_t_OD"] = st.number_input("Minimum t/OD", value=0.0, key="Minimum_t_OD")
    form_values["Minimum_Wall_Thickness"] = st.number_input("Minimum wall thickness (um)", value=0, key="Minimum_Wall_Thickness")
    form_values["Average_Wall_Thickness"] = st.number_input("Average wall thickness (um)", value=0, key="Average_Wall_Thickness")
    form_values["N2_Permeance"] = st.number_input("N2 permeance (GPU)", value=0, key="N2_Permeance")
    form_values["Collapse_Pressure"] = st.number_input("Collapse Pressure (psi)", value=0, key="Collapse_Pressure")
    form_values["Kink_Test_2_95"] = st.number_input("Kink test 2.95 (mm)", value=0.0, key="Kink_Test_2_95")
    form_values["Kink_Test_2_36"] = st.number_input("Kink test 2.36 (mm)", value=0.0, key="Kink_Test_2_36")
    form_values["Order_On_Bobbin"] = st.number_input("Order on bobbin (outside = 1)", value=0, key="Order_On_Bobbin")
    form_values["Number_Of_Blue_Splices"] = st.number_input("Number of blue splices", value=0, key="Number_Of_Blue_Splices")
    form_values["Notes"] = st.text_area("Notes", value="", key="Notes")

# --- SUBMISSION ---
if st.button("Submit Fiber Data"):
    batch_fiber_id = form_values["Batch_Fiber_ID"]
    if not batch_fiber_id:
        st.warning("Batch Fiber ID is required.")
    else:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            form_values["Batch_Fiber_ID"],
            form_values["Supplier_Batch_ID"],
            form_values["Inside_Diameter_Avg"],
            form_values["Inside_Diameter_StDev"],
            form_values["Outside_Diameter_Avg"],
            form_values["Outside_Diameter_StDev"],
            form_values["Reported_Concentricity"],
            form_values["Batch_Length"],
            form_values["Shipment_Date"] if isinstance(form_values["Shipment_Date"], str) else form_values["Shipment_Date"].strftime("%Y-%m-%d"),
            form_values["Tracking_Number"],
            form_values["Fiber_Source"],
            form_values["Average_t_OD"],
            form_values["Minimum_t_OD"],
            form_values["Minimum_Wall_Thickness"],
            form_values["Average_Wall_Thickness"],
            form_values["N2_Permeance"],
            form_values["Collapse_Pressure"],
            form_values["Kink_Test_2_95"],
            form_values["Kink_Test_2_36"],
            form_values["Order_On_Bobbin"],
            form_values["Number_Of_Blue_Splices"],
            form_values["Notes"],
            now_str
        ]
        ufd_sheet.append_row(row, value_input_option="USER_ENTERED")
        st.success(f"Fiber data for Batch Fiber ID {batch_fiber_id} submitted successfully!")
