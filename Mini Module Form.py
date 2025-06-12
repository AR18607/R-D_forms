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
TAB_BATCH_FIBER = "Batch Fiber Tbl"
TAB_UNCOATED_SPOOL = "Uncoated Spool Tbl"
TAB_COATED_SPOOL = "Coated Spool Tbl"
TAB_DCOATING = "Dcoating Tbl"

# ---------- UTILS ----------
def connect_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open(sheet_name)

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        if len(worksheet.row_values(1)) == 0:
            worksheet.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

def get_last_id(worksheet, prefix):
    records = worksheet.col_values(1)[1:]
    nums = [int(r.split('-')[-1]) for r in records if r.startswith(prefix)]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

def generate_c_module_label(operator_initials):
    today = datetime.today().strftime("%Y%m%d")
    base = today + operator_initials.upper()
    labels = mini_sheet.col_values(11)[1:]
    existing = [l.replace(base, '') for l in labels if l.startswith(base)]
    next_letter = chr(ord(max(existing)) + 1) if existing else 'A'
    return base + next_letter

# ---------- LOAD ----------
sheet = connect_google_sheet(GOOGLE_SHEET_NAME)
mini_sheet = get_or_create_tab(sheet, TAB_MINI_MODULE, ["Mini Module ID", "Module ID", "Batch Fiber ID", "UncoatedSpool ID", "CoatedSpool ID", "Dcoating ID", "Number of Fibers", "Fiber Length", "Active Area", "Operator Initials", "Module Label", "Notes", "Date"])
module_sheet = get_or_create_tab(sheet, TAB_MODULE, ["Module ID", "Module Type", "Notes"])
batch_sheet = get_or_create_tab(sheet, TAB_BATCH_FIBER, ["Batch Fiber ID"])
uncoated_sheet = get_or_create_tab(sheet, TAB_UNCOATED_SPOOL, ["UncoatedSpool ID"])
coated_sheet = get_or_create_tab(sheet, TAB_COATED_SPOOL, ["CoatedSpool_ID"])
dcoating_sheet = get_or_create_tab(sheet, TAB_DCOATING, ["Dcoating ID"])

# ---------- FILTERS ----------
module_df = pd.DataFrame(module_sheet.get_all_records())
mini_df = pd.DataFrame(mini_sheet.get_all_records())
mini_modules = module_df[module_df["Module Type"].str.lower() == "mini"]["Module ID"].tolist()
batch_ids = batch_sheet.col_values(1)[1:]
uncoated_ids = uncoated_sheet.col_values(1)[1:]
coated_ids = coated_sheet.col_values(1)[1:]
dcoating_ids = dcoating_sheet.col_values(1)[1:]

# ---------- FORM ----------
st.title("🧪 Mini Module Entry Form")
with st.form("mini_module_form", clear_on_submit=True):
    st.subheader("🔹 Mini Module Entry")

    selected_module = st.selectbox("Module ID (Mini only)", mini_modules)
    existing = mini_df[mini_df["Module ID"] == selected_module]
    prefill = existing.iloc[0] if not existing.empty else None
    mini_module_id = prefill["Mini Module ID"] if prefill is not None else get_last_id(mini_sheet, "MINIMOD")
    st.markdown(f"**Mini Module ID:** `{mini_module_id}`")

    batch_fiber_id = st.selectbox("Batch Fiber ID", batch_ids, index=batch_ids.index(prefill["Batch Fiber ID"]) if prefill else 0)
    uncoated_spool_id = st.selectbox("Uncoated Spool ID", uncoated_ids, index=uncoated_ids.index(prefill["UncoatedSpool ID"]) if prefill else 0)
    coated_spool_id = st.selectbox("Coated Spool ID", coated_ids, index=coated_ids.index(prefill["CoatedSpool ID"]) if prefill else 0)
    dcoating_id = st.selectbox("Dcoating ID", dcoating_ids, index=dcoating_ids.index(prefill["Dcoating ID"]) if prefill else 0)

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
    row = [mini_module_id, selected_module, batch_fiber_id, uncoated_spool_id, coated_spool_id, dcoating_id, num_fibers, fiber_length, active_area, operator_initials, module_label, notes, str(date_val)]
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
