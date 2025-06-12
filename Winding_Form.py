# Winding Form – Final Updated Version with Full Corrections

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
TAB_COATED_SPOOL = "Coated Spool Tbl"

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
wind_program_sheet = get_or_create_tab(sheet, TAB_WIND_PROGRAM, ["Wind Program ID", "Program Name", "Number of bundles / wind", "Number of fibers / ribbon", "Space between ribbons", "Wind Angle (deg)", "Active fiber length (inch)", "Total fiber length (inch)", "Active Area / fiber", "Number of layers", "Number of loops / layer", "C - Active area / layer", "Notes"])
wound_module_sheet = get_or_create_tab(sheet, TAB_WOUND_MODULE, ["Wound Module ID", "Module ID (FK)", "Wind Program ID (FK)", "Operator Initials", "Notes", "MFG DB Wind ID", "MFG DB Potting ID", "MFG DB Mod ID", "Date"])
wrap_sheet = get_or_create_tab(sheet, TAB_WRAP_PER_MODULE, ["WrapPerModule PK", "Module ID (FK)", "Wrap After Layer #", "Type of Wrap", "Notes", "Date"])
spool_sheet = get_or_create_tab(sheet, TAB_SPOOLS_PER_WIND, ["SpoolPerWind PK", "MFG DB Wind ID (FK)", "Coated Spool ID", "Length Used", "Notes", "Date"])
coated_spool_sheet = get_or_create_tab(sheet, TAB_COATED_SPOOL, ["CoatedSpool_ID", "UnCoatedSpool_ID"])

module_df = pd.DataFrame(module_sheet.get_all_records())
wound_module_df = pd.DataFrame(wound_module_sheet.get_all_records())
coated_spool_ids = fetch_column_values(coated_spool_sheet)
wind_program_ids = fetch_column_values(wind_program_sheet)

# Filter Wound Modules only and format with Type
wound_modules = module_df[module_df["Module Type"] == "Wound"]
module_options = [f"{row['Module ID']} ({row['Module Type']})" for _, row in wound_modules.iterrows()]
wind_ids = wound_module_df["Wound Module ID"].dropna().tolist()

st.title("🌀 Winding Form")

col1, col2 = st.columns([2, 3])

# ----------------- WIND PROGRAM FORM -----------------
with col1:
    st.subheader("🌬️ Wind Program")
    selected_existing_wp_id = st.selectbox("Select Wind Program ID to View/Edit", [""] + wind_program_ids)
    wind_program_data = pd.DataFrame(wind_program_sheet.get_all_records())
    wp_prefill = None
    if selected_existing_wp_id:
        match = wind_program_data[wind_program_data["Wind Program ID"] == selected_existing_wp_id]
        if not match.empty:
            wp_prefill = match.iloc[0]

    with st.form("wind_program_form", clear_on_submit=True):
        wind_program_id = selected_existing_wp_id or get_last_id(wind_program_sheet, "WP")
        st.markdown(f"**Wind Program ID:** `{wind_program_id}`")
        program_name = st.text_input("Program Name", value=wp_prefill["Program Name"] if wp_prefill is not None else "")
        bundles = st.number_input("Number of Bundles / Wind", min_value=0, step=1, value=int(wp_prefill["Number of bundles / wind"]) if wp_prefill is not None else 0)
        fibers_per_ribbon = st.number_input("Number of Fibers / Ribbon", min_value=0, step=1, value=int(wp_prefill["Number of fibers / ribbon"]) if wp_prefill is not None else 0)
        spacing = st.number_input("Space Between Ribbons", min_value=0.0, step=0.1, value=float(wp_prefill["Space between ribbons"]) if wp_prefill is not None else 0.0)
        wind_angle = st.number_input("Wind Angle (deg)", min_value=0, step=1, value=int(wp_prefill["Wind Angle (deg)"]) if wp_prefill is not None else 0)
        active_length = st.number_input("Active Fiber Length (inch)", min_value=0.0, value=float(wp_prefill["Active fiber length (inch)"]) if wp_prefill is not None else 0.0)
        total_length = st.number_input("Total Fiber Length (inch)", min_value=0.0, value=float(wp_prefill["Total fiber length (inch)"]) if wp_prefill is not None else 0.0)
        active_area = st.number_input("Active Area / Fiber", min_value=0.0, value=float(wp_prefill["Active Area / fiber"]) if wp_prefill is not None else 0.0)
        layers = st.number_input("Number of Layers", min_value=0, step=1, value=int(wp_prefill["Number of layers"]) if wp_prefill is not None else 0)
        loops_per_layer = st.number_input("Number of Loops / Layer", min_value=0, step=1, value=int(wp_prefill["Number of loops / layer"]) if wp_prefill is not None else 0)
        area_layer = st.number_input("C - Active Area / Layer", min_value=0.0, value=float(wp_prefill["C - Active area / layer"]) if wp_prefill is not None else 0.0)
        notes = st.text_area("Notes", value=wp_prefill["Notes"] if wp_prefill is not None else "")
        if st.form_submit_button("💾 Save Wind Program"):
            new_entry = [wind_program_id, program_name, bundles, fibers_per_ribbon, spacing, wind_angle, active_length, total_length, active_area, layers, loops_per_layer, area_layer, notes]
            if selected_existing_wp_id and selected_existing_wp_id in wind_program_data["Wind Program ID"].values:
                idx = wind_program_data[wind_program_data["Wind Program ID"] == selected_existing_wp_id].index[0] + 2
                wind_program_sheet.delete_rows(idx)
                wind_program_sheet.insert_row(new_entry, idx)
                st.success(f"✅ Wind Program `{wind_program_id}` updated.")
            else:
                wind_program_sheet.append_row(new_entry)
                st.success(f"✅ Wind Program `{wind_program_id}` saved.")

# ----------------- OTHER FORMS STACKED -----------------
with col2:
    st.subheader("🧵 Wound Module")
    with st.form("wound_module_form", clear_on_submit=True):
        wound_id = get_last_id(wound_module_sheet, "WMOD", start_at=72)
        st.markdown(f"Wound Module ID: `{wound_id}`")
        selected_module = st.selectbox("Module ID", module_options)
        wind_fk = st.selectbox("Wind Program ID", wind_ids)
        operator = st.text_input("Operator Initials")
        notes = st.text_area("Notes")
        mfg_wind = st.text_input("MFG DB Wind ID")
        mfg_potting = st.text_input("MFG DB Potting ID")
        mfg_mod = st.number_input("MFG DB Mod ID", min_value=0, step=1)
        entry_date = st.date_input("Date", value=datetime.today())
        if st.form_submit_button("💾 Save Wound Module"):
            module_fk = selected_module.split(" ")[0]
            wound_module_sheet.append_row([wound_id, module_fk, wind_fk, operator, notes, mfg_wind, mfg_potting, mfg_mod, entry_date.strftime("%Y-%m-%d")])
            st.success(f"✅ Saved {wound_id}")

    # Wrap Per Module
    st.subheader("🎁 Wrap Per Module")
    if "wrap_entries" not in st.session_state:
        st.session_state.wrap_entries = []
    with st.form("wrap_form"):
        wrap_id = get_last_id(wrap_sheet, "WRAP")
        st.markdown(f"Wrap PK: `{wrap_id}`")
        wrap_mod = st.selectbox("Module ID", module_options)
        after_layer = st.number_input("Wrap After Layer #", min_value=0)
        wrap_type = st.selectbox("Type of Wrap", ["Teflon", "Nylon", "Other"])
        wrap_notes = st.text_area("Notes")
        wrap_date = st.date_input("Date", value=datetime.today())
        if st.form_submit_button("➕ Add Wrap"):
            st.session_state.wrap_entries.append([wrap_id, wrap_mod.split(" ")[0], after_layer, wrap_type, wrap_notes, wrap_date.strftime("%Y-%m-%d")])
    if st.session_state.wrap_entries:
        st.dataframe(pd.DataFrame(st.session_state.wrap_entries, columns=["PK", "Mod", "Layer", "Type", "Notes", "Date"]))
        if st.button("💾 Submit All Wraps"):
            for entry in st.session_state.wrap_entries:
                wrap_sheet.append_row(entry)
            st.success("✅ Wraps submitted")
            st.session_state.wrap_entries.clear()

    # Spools Per Wind
    st.subheader("🧪 Spools Per Wind")
    if "spool_entries" not in st.session_state:
        st.session_state.spool_entries = []
    with st.form("spool_form"):
        spool_id = get_last_id(spool_sheet, "SPW")
        wind_fk = st.selectbox("Wind ID", wind_ids)
        coated_fk = st.selectbox("Coated Spool ID", coated_spool_ids)
        length = st.number_input("Length Used", min_value=0.0)
        notes = st.text_area("Notes")
        spool_date = st.date_input("Date", value=datetime.today())
        if st.form_submit_button("➕ Add Spool"):
            st.session_state.spool_entries.append([spool_id, wind_fk, coated_fk, length, notes, spool_date.strftime("%Y-%m-%d")])
    if st.session_state.spool_entries:
        st.dataframe(pd.DataFrame(st.session_state.spool_entries, columns=["ID", "Wind", "Spool", "Length", "Notes", "Date"]))
        if st.button("💾 Submit All Spools"):
            for entry in st.session_state.spool_entries:
                spool_sheet.append_row(entry)
            st.success("✅ Spools submitted")
            st.session_state.spool_entries.clear()

# ------------------ 30-DAY DATA REVIEW ------------------
st.subheader("📅 Recent Entries (Last 30 Days)")
review_tables = {
    "Module Tbl": (module_sheet, "Module ID"),
    "Wind Program Tbl": (wind_program_sheet, "Wind Program ID"),
    "Wound Module Tbl": (wound_module_sheet, "Date"),
    "Wrap per Module Tbl": (wrap_sheet, "Date"),
    "Spools per Wind Tbl": (spool_sheet, "Date")
}

for label, (ws, date_col) in review_tables.items():
    st.markdown(f"### {label}")
    try:
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
            if date_col in df.columns:
                cutoff = datetime.today().date() - timedelta(days=30)
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date
                df = df[df[date_col] >= cutoff]

                st.dataframe(df.sort_values(by=date_col, ascending=False))
            else:
                st.dataframe(df)
        else:
            st.info("No recent entries.")
    except Exception as e:
        st.error(f"❌ Failed to load {label}: {e}")
