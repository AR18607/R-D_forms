import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ---------------- CONFIG ----------------
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1AGZ1g3LeSPtLAKV685snVQeERWXVPF4WlIAV8aAj9o8"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

TAB_RESPOOLING = "Respooling Tbl"

# ---------------- FUNCTIONS ----------------
def connect_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client.open_by_url(GOOGLE_SHEET_URL)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_column_a_values(worksheet):
    values = worksheet.col_values(1)[1:]  # Skip header
    return [str(v).strip() for v in values if str(v).strip() != ""]

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def get_recent_entries_df(sheet, headers):
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        cutoff_date = pd.to_datetime(datetime.today() - timedelta(days=7))
        df = df[df["Date"] >= cutoff_date]
    return df[headers] if not df.empty else pd.DataFrame(columns=headers)

# ---------------- INIT ----------------
st.title("🌀 Respooling Form")
spreadsheet = connect_google_sheet()

# Get all tabs by index
all_sheets = spreadsheet.worksheets()
st.write("DEBUG - Tabs available:", [ws.title for ws in all_sheets])

# Respooling sheet by name
respooling_headers = ["Respooling ID", "Spool Type", "Spool ID", "Length List", "Date", "Initials", "Label", "Notes"]
respooling_sheet = get_or_create_tab(spreadsheet, TAB_RESPOOLING, respooling_headers)

# Load coated/uncoated sheets by position
coated_sheet = all_sheets[0]   # 🟡 First tab
uncoated_sheet = all_sheets[1] # 🟡 Second tab

# ---------------- FORM ENTRY ----------------
st.subheader("📋 Respooling Entry")

spool_type = st.selectbox("Are you respooled fiber from:", ["Coated", "Uncoated"], key="spool_type")

if spool_type == "Coated":
    spool_ids = get_column_a_values(coated_sheet)
    st.write("DEBUG - Coated Spool IDs from Column A:", spool_ids)
else:
    spool_ids = get_column_a_values(uncoated_sheet)
    st.write("DEBUG - Uncoated Spool IDs from Column A:", spool_ids)

if not spool_ids:
    st.warning(f"No spool IDs found for '{spool_type}' fiber. Please check column A in the correct sheet.")
    selected_spool_id = None
else:
    selected_spool_id = st.selectbox("Select Spool ID", spool_ids, key="spool_id")

if "num_spools" not in st.session_state:
    st.session_state.num_spools = 1

st.session_state.num_spools = st.number_input(
    "How many spools are you making from this fiber?",
    min_value=1,
    step=1,
    value=st.session_state.num_spools,
    key="num_spools_input"
)

# ---------------- FORM ----------------
with st.form("respooling_form"):
    respooling_id = get_last_id(respooling_sheet, "RSP")
    st.markdown(f"**Auto-generated Respooling ID:** ` {respooling_id} `")

    lengths = []
    for i in range(int(st.session_state.num_spools)):
        length = st.number_input(
            f"Length for Spool #{i + 1} (m)",
            min_value=0.0,
            format="%.2f",
            key=f"length_input_{i}_{st.session_state.num_spools}"
        )
        lengths.append(length)

    date = st.date_input("Date")
    initials = st.text_input("Initials")
    label = st.text_input("Label")
    notes = st.text_area("Notes")
    submit = st.form_submit_button("💾 Submit")

# ---------------- SUBMIT ----------------
if submit:
    if not selected_spool_id:
        st.error("❌ Please select a valid Spool ID before submitting.")
    else:
        try:
            respooling_sheet.append_row([
                respooling_id,
                spool_type,
                selected_spool_id,
                ", ".join([str(l) for l in lengths]),
                str(date),
                initials,
                label,
                notes
            ])
            st.success("✅ Respooling record successfully saved!")
        except Exception as e:
            st.error(f"❌ Error saving data: {e}")

# ---------------- 7-DAY REVIEW ----------------
st.markdown("---")
st.subheader("📅 Recent Respooling Entries (Last 7 Days)")
df_recent = get_recent_entries_df(respooling_sheet, respooling_headers)
st.dataframe(df_recent if not df_recent.empty else pd.DataFrame(columns=respooling_headers))
