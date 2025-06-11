# Winding Form – Updated with Corrections

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import pandas as pd

# ----------------- CONFIG -----------------
GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_CREDENTIALS = json.loads(st.secrets["gcp_service_account"])

TAB_MODULE = "Module Tbl"
TAB_WIND_PROGRAM = "Wind Program Tbl"
TAB_WOUND_MODULE = "Wound Module Tbl"
TAB_WRAP_PER_MODULE = "Wrap per Module Tbl"
TAB_SPOOLS_PER_WIND = "Spools per Wind Tbl"

# ----------------- UTILS -----------------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_or_create_tab(sheet, tab_name, headers):
    for ws in sheet.worksheets():
        if ws.title.strip().lower() == tab_name.strip().lower():
            return ws
    ws = sheet.add_worksheet(title=tab_name, rows="1000", cols="50")
    ws.insert_row(headers, 1)
    return ws

def get_last_id(worksheet, prefix, start_at=72):
    records = worksheet.col_values(1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix) and r.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else start_at
    return f"{prefix}-{str(next_num).zfill(3)}"

def fetch_column_values(worksheet, col_index=1):
    return [v for v in worksheet.col_values(col_index)[1:] if v]

# ----------------- CONNECT SHEETS -----------------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
module_sheet = get_or_create_tab(sheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
wind_program_sheet = get_or_create_tab(sheet, TAB_WIND_PROGRAM, [...])
wound_module_sheet = get_or_create_tab(sheet, TAB_WOUND_MODULE, [...])
wrap_sheet = get_or_create_tab(sheet, TAB_WRAP_PER_MODULE, [...])
spool_sheet = get_or_create_tab(sheet, TAB_SPOOLS_PER_WIND, [...])

# Filter Wound Modules only
module_df = pd.DataFrame(module_sheet.get_all_records())
wound_modules = module_df[module_df["Module Type"] == "Wound"]["Module ID"].tolist()
wind_ids = fetch_column_values(wound_module_sheet, 1)
spool_ids = fetch_column_values(spool_sheet, 3)  # Assuming Coated Spool ID is col 3

# ----------------- LAYOUT -----------------
col1, col2 = st.columns([2, 3])

# ----------------- WIND PROGRAM FORM -----------------
with col1:
    st.subheader("🌬️ Wind Program")
    with st.form("wind_program_form", clear_on_submit=True):
        # wind_program_id = ...
        # all inputs for wind program form here
        if st.form_submit_button("💾 Save Wind Program"):
            # logic to append/update sheet
            pass

# ----------------- OTHER FORMS STACKED -----------------
with col2:
    st.subheader("🧵 Wound Module")
    with st.form("wound_module_form", clear_on_submit=True):
        wound_id = get_last_id(wound_module_sheet, "WMOD")
        st.markdown(f"**Wound Module ID:** `{wound_id}`")
        module_fk = st.selectbox("Module ID", wound_modules)
        wind_fk = st.selectbox("Wind Program ID", wind_ids)
        if st.form_submit_button("💾 Save Wound Module"):
            # append row to wound_module_sheet
            pass

    st.subheader("🎁 Wrap Per Module")
    if "wrap_entries" not in st.session_state:
        st.session_state.wrap_entries = []
    with st.form("wrap_form"):
        wrap_id = get_last_id(wrap_sheet, "WRAP")
        st.markdown(f"Wrap PK: `{wrap_id}`")
        # form fields
        if st.form_submit_button("➕ Add Wrap"):
            st.session_state.wrap_entries.append({...})
    if st.session_state.wrap_entries:
        st.dataframe(pd.DataFrame(st.session_state.wrap_entries))
        if st.button("💾 Submit All Wraps"):
            for wrap in st.session_state.wrap_entries:
                wrap_sheet.append_row([...])
            st.session_state.wrap_entries.clear()

    st.subheader("🧪 Spools Per Wind")
    if "spool_entries" not in st.session_state:
        st.session_state.spool_entries = []
    with st.form("spool_form"):
        spool_id = get_last_id(spool_sheet, "SPW")
        st.markdown(f"Spool PK: `{spool_id}`")
        wind_dropdown = st.selectbox("Wind ID", wind_ids)
        coated_dropdown = st.selectbox("Coated Spool ID", spool_ids)
        # other inputs
        if st.form_submit_button("➕ Add Spool"):
            st.session_state.spool_entries.append({...})
    if st.session_state.spool_entries:
        st.dataframe(pd.DataFrame(st.session_state.spool_entries))
        if st.button("💾 Submit All Spools"):
            for spool in st.session_state.spool_entries:
                spool_sheet.append_row([...])
            st.session_state.spool_entries.clear()

# ------------------ 7-DAY DATA REVIEW ------------------
st.subheader("📅 Recent Entries (Last 30 Days)")

review_tables = {
    "📦 Module Entries": (module_sheet, "Module ID"),
    "🌬️ Wind Program Entries": (wind_program_sheet, "Date"),
    "🧵 Wound Module Entries": (wound_module_sheet, "Date"),
    "🎁 Wrap Per Module Entries": (wrap_sheet, "Date"),
    "🧪 Spools Per Wind Entries": (spool_sheet, "Date")
}

for label, (ws, date_col) in review_tables.items():
    st.markdown(f"### {label}")
    try:
        df = pd.DataFrame(ws.get_all_records())
        df.columns = [col.strip() for col in df.columns]
        if not df.empty and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df[df[date_col].notna()]
            df = df[df[date_col].dt.date >= (datetime.now().date() - timedelta(days=30))]
            if not df.empty:
                st.dataframe(df.sort_values(by=date_col, ascending=False))
            else:
                st.info("No recent entries in the last 30 days.")
        else:
            st.info("No entries or missing date column.")
    except Exception as e:
        st.error(f"Error loading `{label}`: {e}")
