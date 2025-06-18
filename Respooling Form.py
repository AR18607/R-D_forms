import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# ---------------- CONFIG ----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

# Sheet Tab Names
TAB_RESPOOLING = "Respooling Tbl"
TAB_COATED_SPOOL = "Coated Spool Tbl"
TAB_UNCOATED_SPOOL = "UnCoatedSpool ID Tbl"

# ---------------- FUNCTIONS ----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, id_prefix):
    records = worksheet.col_values(1)[1:]
    if not records:
        return f"{id_prefix}-001"
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(id_prefix)]
    next_num = max(nums) + 1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def get_foreign_key_options(worksheet, id_col=1):
    return worksheet.col_values(id_col)[1:]

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
spreadsheet = connect_google_sheet(GOOGLE_SHEET_NAME)

respooling_headers = ["Respooling ID", "Spool Type", "Spool ID", "Length List", "Date", "Initials", "Label", "Notes"]
respooling_sheet = get_or_create_tab(spreadsheet, TAB_RESPOOLING, respooling_headers)
coated_spool_sheet = get_or_create_tab(spreadsheet, TAB_COATED_SPOOL, ["CoatedSpool ID"])
uncoated_spool_sheet = get_or_create_tab(spreadsheet, TAB_UNCOATED_SPOOL, ["UnCoatedSpool ID"])

# ---------------- FORM ----------------
with st.form("respooling_form"):
    st.subheader("📋 Respooling Entry")
    respooling_id = get_last_id(respooling_sheet, "RSP")
    st.markdown(f"**Auto-generated Respooling ID:** `{respooling_id}`")

    spool_type = st.selectbox("Are you respooled fiber from:", ["Coated", "Uncoated"])
    spool_ids = get_foreign_key_options(coated_spool_sheet if spool_type == "Coated" else uncoated_spool_sheet)
    selected_spool_id = st.selectbox("Select Spool ID", spool_ids)

    num_spools = st.number_input("How many spools are you making from this fiber?", min_value=1, step=1, key="num_spools")

    lengths = []
    for i in range(int(st.session_state.num_spools)):
        length = st.number_input(f"Length for Spool #{i + 1} (m)", min_value=0.0, format="%.2f", key=f"length_{i}")
        lengths.append(length)

    date = st.date_input("Date")
    initials = st.text_input("Initials")
    label = st.text_input("Label")
    notes = st.text_area("Notes")

    submit = st.form_submit_button("📅 Submit")

if submit:
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

# ---------------- 7-DAY PREVIEW ----------------
st.markdown("---")
st.subheader("🗓️ Recent Respooling Entries (Last 7 Days)")
df_recent = get_recent_entries_df(respooling_sheet, respooling_headers)
st.dataframe(df_recent if not df_recent.empty else pd.DataFrame(columns=respooling_headers))
