import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# ---------- CONFIG ----------
GOOGLE_SHEET_NAME = "R&D Data Form"
TAB_MINI_MODULE = "Mini Module Tbl"
TAB_MODULE = "Module Tbl"
TAB_BATCH_FIBER = "Uncoated Fiber Data Tbl"
TAB_UNCOATED_SPOOL = "UnCoatedSpool ID Tbl"
TAB_COATED_SPOOL = "Coated Spool Tbl (Used)"
TAB_DCOATING = "Dip Coating Process Tbl"

# ---------- UTILS ----------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        if not worksheet.get_all_values():
            worksheet.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, prefix):
    records = worksheet.col_values(1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix) and r.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

def generate_c_module_label(operator_initials):
    today = datetime.today().strftime("%Y%m%d")
    base = today + operator_initials.upper()
    labels = mini_sheet.col_values(11)[1:]
    existing = [l.replace(base, '') for l in labels if l.startswith(base)]
    next_letter = chr(ord(max(existing)) + 1) if existing else 'A'
    return base + next_letter

# ---------- LOAD SHEETS ----------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)

mini_sheet = get_or_create_tab(sheet, TAB_MINI_MODULE, [
    "Mini Module ID", "Module ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "CoatedSpool_ID", "DCoating_ID",
    "Number of Fibers", "Fiber Length", "Active Area", "Operator Initials", "Module Label", "Notes", "Date"
])

module_sheet = get_or_create_tab(sheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
batch_sheet = get_or_create_tab(sheet, TAB_BATCH_FIBER, ["Batch_Fiber_ID"])
uncoated_sheet = get_or_create_tab(sheet, TAB_UNCOATED_SPOOL, ["UncoatedSpool_ID"])
coated_sheet = get_or_create_tab(sheet, TAB_COATED_SPOOL, ["CoatedSpool_ID", "UnCoatedSpool_ID"])  # ✅ FIXED HEADERS
dcoating_sheet = get_or_create_tab(sheet, TAB_DCOATING, [
    "DCoating_ID", "Solution_ID", "Date", "Box_Temperature", "Box_RH", "N2_Flow",
    "Number_of_Fibers", "Coating_Speed", "Annealing_Time", "Annealing_Temperature",
    "Coating_Layer_Type", "Operator_Initials", "Ambient_Temperature", "Ambient_RH", "Notes"
])

# ---------- LOAD DATA ----------
module_df = pd.DataFrame(module_sheet.get_all_records())
mini_df = pd.DataFrame(mini_sheet.get_all_records())
batch_df = pd.DataFrame(batch_sheet.get_all_records())
uncoated_df = pd.DataFrame(uncoated_sheet.get_all_records())
coated_df = pd.DataFrame(coated_sheet.get_all_records())
dcoating_df = pd.DataFrame(dcoating_sheet.get_all_records())

mini_modules = module_df[module_df["Module Type"].str.lower() == "mini"]["Module ID"].tolist()
batch_ids = batch_df.get("Batch_Fiber_ID", pd.Series()).dropna().tolist()
uncoated_ids = uncoated_df.get("UncoatedSpool_ID", pd.Series()).dropna().tolist()
coated_ids = coated_df.get("CoatedSpool_ID", pd.Series()).dropna().tolist()
dcoating_ids = dcoating_df.get("DCoating_ID", pd.Series()).dropna().tolist()

# ---------- FORM ----------
st.title("🧪 Mini Module Entry Form")
with st.form("mini_module_form", clear_on_submit=True):
    st.subheader("🔹 Mini Module Entry")

    selected_module = st.selectbox("Module ID (Mini only)", mini_modules)
    existing = mini_df[mini_df["Module ID"] == selected_module]
    prefill = existing.iloc[0] if not existing.empty else None

    mini_module_id = prefill["Mini Module ID"] if prefill is not None else get_last_id(mini_sheet, "MINIMOD")
    st.markdown(f"**Mini Module ID:** `{mini_module_id}`")

    batch_fiber_id = st.selectbox("Batch_Fiber_ID", batch_ids, index=batch_ids.index(prefill["Batch_Fiber_ID"]) if prefill else 0)
    uncoated_spool_id = st.selectbox("UncoatedSpool_ID", uncoated_ids, index=uncoated_ids.index(prefill["UncoatedSpool_ID"]) if prefill else 0)
    coated_spool_id = st.selectbox("CoatedSpool_ID", coated_ids, index=coated_ids.index(prefill["CoatedSpool_ID"]) if prefill and prefill["CoatedSpool_ID"] in coated_ids else 0)
    dcoating_id = st.selectbox("DCoating_ID", dcoating_ids, index=dcoating_ids.index(prefill["DCoating_ID"]) if prefill and prefill["DCoating_ID"] in dcoating_ids else 0)

    num_fibers = st.number_input("Number of Fibers", step=1, value=int(prefill["Number of Fibers"]) if prefill else 0)
    fiber_length = st.number_input("Fiber Length (inches)", format="%.2f", value=float(prefill["Fiber Length"]) if prefill else 0.0)
    active_area = st.number_input("C - Active Area", format="%.2f", value=float(prefill["Active Area"]) if prefill else 0.0)
    operator_initials = st.text_input("Operator Initials", value=prefill["Operator Initials"] if prefill else "")
    auto_label = st.checkbox("Auto-generate C-Module Label?", value=True)
    module_label = generate_c_module_label(operator_initials) if auto_label and operator_initials else st.text_input("C-Module Label", value=prefill["Module Label"] if prefill else "")
    notes = st.text_area("Notes", value=prefill["Notes"] if prefill else "")
    date_val = st.date_input("Date", value=datetime.today().date() if prefill is None else datetime.strptime(prefill["Date"], "%Y-%m-%d").date())

    submit = st.form_submit_button("💾 Save Entry")

# ---------- SAVE ----------
if submit:
    row = [
        mini_module_id, selected_module, batch_fiber_id, uncoated_spool_id,
        coated_spool_id, dcoating_id, num_fibers, fiber_length, active_area,
        operator_initials, module_label, notes, str(date_val)
    ]
    try:
        if prefill is not None:
            idx = mini_df[mini_df["Mini Module ID"] == mini_module_id].index[0] + 2
            mini_sheet.delete_rows(idx)
            mini_sheet.insert_row(row, idx)
            st.success("✅ Entry updated.")
        else:
            mini_sheet.append_row(row)
            st.success("✅ Entry saved.")
    except Exception as e:
        st.error(f"❌ Error saving: {e}")

# ---------- LAST 7 DAYS ----------
st.subheader("📅 Mini Modules: Last 7 Days")
if not mini_df.empty:
    mini_df["Date"] = pd.to_datetime(mini_df["Date"], errors="coerce")
    recent = mini_df[mini_df["Date"] >= datetime.today() - timedelta(days=7)]
    if not recent.empty:
        st.dataframe(recent)
    else:
        st.info("No entries in last 7 days.")
else:
    st.info("No data yet.")
