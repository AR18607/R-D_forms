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

# === HEADERS (MATCH YOUR GOOGLE SHEET TABLES) ===
UFD_HEADERS = [
    "Batch_Fiber_ID", "Supplier_Batch_ID", "Inside_Diameter_Avg", "Inside_Diameter_StDev",
    "Outside_Diameter_Avg", "Outside_Diameter_StDev", "Reported_Concentricity", "Batch_Length",
    "Shipment_Date", "Tracking_Number", "Fiber_Source", "Average_t_OD", "Minimum_t_OD",
    "Minimum_Wall_Thickness", "Average_Wall_Thickness", "N2_Permeance", "Collapse_Pressure",
    "Kink_Test_2_95", "Kink_Test_2_36", "Order_On_Bobbin", "Number_Of_Blue_Splices", "Notes", "Date_Time"
]
USID_HEADERS = ["UncoatedSpool_ID", "Type", "C_Length", "Date_Time"]
AR_HEADERS = ["Received_Spool_PK", "UncoatedSpool_ID", "Batch_Fiber_ID", "Notes", "Date_Time"]
CS_HEADERS = ["Combined_SpoolsPK", "UncoatedSpool_ID", "Received_Spool_PK", "Date_Time"]
QC_HEADERS = [
    "Ardent_QC_ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "Ardent_QC_Inside_Diameter",
    "Ardent_QC_Outside_Diameter", "Measured_Concentricity", "Wall_Thickness",
    "Operator_Initials", "Notes", "Date_Time", "Inside_Circularity", "Outside_Circularity"
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

def get_next_id(worksheet, id_column):
    records = worksheet.get_all_records()
    if records:
        last_id = max([int(record[id_column]) for record in records if str(record[id_column]).isdigit()])
        return last_id + 1
    return 1

def get_or_create_worksheet(sheet, title, headers):
    try:
        worksheet = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=title, rows="1000", cols="50")
        worksheet.append_row(headers)
    return worksheet

# === TABLE SHEETS ===
ufd_sheet = get_or_create_worksheet(spreadsheet, "Uncoated Fiber Data Tbl", UFD_HEADERS)
usid_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", USID_HEADERS)
ar_sheet = get_or_create_worksheet(spreadsheet, "As Received UnCoatedSpools Tbl", AR_HEADERS)
cs_sheet = get_or_create_worksheet(spreadsheet, "Combined Spools Tbl", CS_HEADERS)
qc_sheet = get_or_create_worksheet(spreadsheet, "Ardent Fiber Dimension QC Tbl", QC_HEADERS)

# === UNCOATED FIBER DATA ENTRY ===
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

# === UNCOATED SPOOL ID TABLE ===
st.header("UnCoatedSpool ID Entry")
spool_type = st.selectbox("Type", ["As received", "Combined"], key="usid_type")
c_length = st.number_input("C-Length (sum of batch lengths on the spool)", value=0.0, key="usid_c_length")
usid_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.button("Submit UnCoatedSpool ID", on_click=lambda: usid_sheet.append_row(
    [get_next_id(usid_sheet, "UncoatedSpool_ID"), spool_type, c_length, usid_now]
))

# === AS RECEIVED UNCOATED SPOOLS TABLE ===
st.header("As Received UnCoatedSpools Entry")
uncoated_spool_ids = [str(record["UncoatedSpool_ID"]) for record in usid_sheet.get_all_records() if record.get("UncoatedSpool_ID")]
batch_fiber_ids = [str(record["Batch_Fiber_ID"]) for record in ufd_sheet.get_all_records() if record.get("Batch_Fiber_ID")]
ar_notes = st.text_area("Notes for As Received UnCoatedSpools", key="ar_notes")
if not uncoated_spool_ids or not batch_fiber_ids:
    st.warning("⚠️ Please ensure both UncoatedSpool IDs and Batch Fiber IDs are available before submitting.")
    st.selectbox("UncoatedSpool ID", uncoated_spool_ids or ["No IDs available"], key="ar_usid", disabled=True)
    st.selectbox("Batch Fiber ID", batch_fiber_ids or ["No IDs available"], key="ar_bfid", disabled=True)
    st.button("Submit As Received UnCoatedSpools", disabled=True)
else:
    selected_usid = st.selectbox("UncoatedSpool ID", uncoated_spool_ids, key="ar_usid")
    selected_bfid = st.selectbox("Batch Fiber ID", batch_fiber_ids, key="ar_bfid")
    if st.button("Submit As Received UnCoatedSpools"):
        next_ar_pk = get_next_id(ar_sheet, "Received_Spool_PK")
        ar_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ar_sheet.append_row([next_ar_pk, selected_usid, selected_bfid, ar_notes, ar_now])
        st.success(f"As Received UnCoatedSpools PK {next_ar_pk} submitted.")

# === COMBINED SPOOLS TABLE ===
st.header("Combined Spools Entry")
received_spool_pks = [str(record["Received_Spool_PK"]) for record in ar_sheet.get_all_records() if record.get("Received_Spool_PK")]
if not uncoated_spool_ids or not received_spool_pks:
    st.warning("⚠️ Please ensure both UncoatedSpool IDs and Received Spool PKs are available before submitting.")
    st.selectbox("UncoatedSpool ID for Combined", uncoated_spool_ids or ["No IDs available"], key="cs_usid", disabled=True)
    st.selectbox("Received Spool PK", received_spool_pks or ["No PKs available"], key="cs_rspk", disabled=True)
    st.button("Submit Combined Spools", disabled=True)
else:
    selected_usid_c = st.selectbox("UncoatedSpool ID for Combined", uncoated_spool_ids, key="cs_usid")
    selected_rspk = st.selectbox("Received Spool PK", received_spool_pks, key="cs_rspk")
    if st.button("Submit Combined Spools"):
        next_cs_pk = get_next_id(cs_sheet, "Combined_SpoolsPK")
        cs_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cs_sheet.append_row([next_cs_pk, selected_usid_c, selected_rspk, cs_now])
        st.success(f"Combined Spools PK {next_cs_pk} submitted.")

# === ARDENT FIBER DIMENSION QC TABLE ===
st.header("Ardent Fiber Dimension QC Entry")
if not batch_fiber_ids or not uncoated_spool_ids:
    st.warning("⚠️ Please ensure Batch Fiber IDs and UncoatedSpool IDs are available before entering QC data.")
    st.selectbox("Batch Fiber ID for QC", batch_fiber_ids or ["No IDs available"], key="qc_bfid", disabled=True)
    st.selectbox("UncoatedSpool ID for QC", uncoated_spool_ids or ["No IDs available"], key="qc_usid", disabled=True)
    st.number_input("Ardent QC Inside Diameter (um)", value=0.0, key="qc_id", disabled=True)
    st.number_input("Ardent QC Outside Diameter (um)", value=0.0, key="qc_od", disabled=True)
    st.number_input("Measured Concentricity (%)", value=0.0, key="qc_conc", disabled=True)
    st.number_input("Wall Thickness (um)", value=0.0, key="qc_wall", disabled=True)
    st.text_input("Operator Initials", key="qc_init", disabled=True)
    st.text_area("Notes for QC", key="qc_notes", disabled=True)
    st.date_input("Date", value=datetime.today(), key="qc_date", disabled=True)
    st.number_input("Inside Circularity", value=0.0, key="qc_ic", disabled=True)
    st.number_input("Outside Circularity", value=0.0, key="qc_oc", disabled=True)
    st.button("Submit Fiber Dimension QC", disabled=True)
else:
    selected_bfid_qc = st.selectbox("Batch Fiber ID for QC", batch_fiber_ids, key="qc_bfid")
    selected_usid_qc = st.selectbox("UncoatedSpool ID for QC", uncoated_spool_ids, key="qc_usid")
    ardent_qc_inside_d = st.number_input("Ardent QC Inside Diameter (um)", value=0.0, key="qc_id")
    ardent_qc_outside_d = st.number_input("Ardent QC Outside Diameter (um)", value=0.0, key="qc_od")
    measured_conc = st.number_input("Measured Concentricity (%)", value=0.0, key="qc_conc")
    wall_thick = st.number_input("Wall Thickness (um)", value=0.0, key="qc_wall")
    operator_init = st.text_input("Operator Initials", key="qc_init")
    qc_notes = st.text_area("Notes for QC", key="qc_notes")
    qc_date = st.date_input("Date", value=datetime.today(), key="qc_date")
    inside_circ = st.number_input("Inside Circularity", value=0.0, key="qc_ic")
    outside_circ = st.number_input("Outside Circularity", value=0.0, key="qc_oc")
    if st.button("Submit Fiber Dimension QC"):
        next_qc_id = get_next_id(qc_sheet, "Ardent_QC_ID")
        qc_now = qc_date.strftime("%Y-%m-%d %H:%M:%S")
        qc_sheet.append_row([
            next_qc_id, selected_bfid_qc, selected_usid_qc, ardent_qc_inside_d,
            ardent_qc_outside_d, measured_conc, wall_thick, operator_init,
            qc_notes, qc_now, inside_circ, outside_circ
        ])
        st.success(f"Ardent QC Entry ID {next_qc_id} submitted.")

# === 7 DAY PREVIEW ===
from datetime import timedelta

def parse_datetime_str(dt_str):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(dt_str).strip(), fmt)
        except Exception:
            continue
    return None

def filter_last_7_days(records, date_key="Date_Time"):
    today = datetime.today()
    filtered_records = []
    for record in records:
        dt_str = record.get(date_key, "").strip()
        parsed = parse_datetime_str(dt_str)
        if parsed and parsed.date() >= (today - timedelta(days=7)).date():
            filtered_records.append(record)
    return filtered_records

def show_table_preview(title, worksheet, date_col="Date_Time"):
    st.markdown(f"#### {title}")
    records = worksheet.get_all_records()
    filtered = filter_last_7_days(records, date_col)
    if filtered:
        st.dataframe(pd.DataFrame(filtered))
    else:
        st.info("No records in the last 7 days.")

st.markdown("## 📅 Last 7 Days Data Preview")
show_table_preview("🧪 Uncoated Fiber Data", ufd_sheet, "Date_Time")
show_table_preview("🧵 UnCoatedSpool ID", usid_sheet, "Date_Time")
show_table_preview("📦 As Received UncoatedSpools", ar_sheet, "Date_Time")
show_table_preview("🔗 Combined Spools", cs_sheet, "Date_Time")
show_table_preview("🧪 Ardent Fiber Dimension QC", qc_sheet, "Date_Time")
