import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
import time

#GOOGLE_SHEET_NAME = "R&D Data Form"
GOOGLE_SHEET_NAME = "R&D Data Form – TEMP TEST"

TAB_MINI_MODULE = "Mini Module Tbl"
TAB_MODULE = "Module Tbl"
TAB_BATCH_FIBER = "Uncoated Fiber Data Tbl"
TAB_UNCOATED_SPOOL = "UnCoatedSpool ID Tbl"
TAB_COATED_SPOOL = "Coated Spool Tbl"
TAB_DCOATING = "Dip Coating Process Tbl"

# --- Google Client Connect ---
@st.cache_resource
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = json.loads(st.secrets["gcp_service_account"])
    creds_json["private_key"] = creds_json["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    return gspread.authorize(creds)

# --- Data Load from Google Sheets (on-demand only) ---
def load_all_tab_data():
    try:
        gc = get_gsheet_client()
        sh = gc.open(GOOGLE_SHEET_NAME)
        # Each worksheet, with fallback for missing
        def load_tab(tab, headers):
            try:
                ws = sh.worksheet(tab)
                if headers and not ws.get_all_values():
                    ws.insert_row(headers, 1)
                df = pd.DataFrame(ws.get_all_records())
                return df
            except gspread.exceptions.WorksheetNotFound:
                ws = sh.add_worksheet(title=tab, rows="1000", cols="50")
                ws.insert_row(headers, 1)
                return pd.DataFrame(ws.get_all_records())
        # Define all headers
        mini_headers = [
            "Mini Module ID", "Module ID", "Batch_Fiber_ID", "UncoatedSpool_ID", "CoatedSpool_ID", "DCoating_ID",
            "Number of Fibers", "Fiber Length", "Active Area", "Operator Initials", "Module Label", "Notes", "Date"
        ]
        module_headers = ["Module ID", "Module Type", "Notes"]
        batch_headers = ["Batch_Fiber_ID"]
        uncoated_headers = ["UncoatedSpool_ID"]
        coated_headers = ["CoatedSpool_ID"]
        dcoating_headers = [
            "DCoating_ID", "Solution_ID", "Date", "Box_Temperature", "Box_RH", "N2_Flow",
            "Number_of_Fibers", "Coating_Speed", "Annealing_Time", "Annealing_Temperature",
            "Coating_Layer_Type", "Operator_Initials", "Ambient_Temperature", "Ambient_RH", "Notes"
        ]
        return {
            "mini_df": load_tab(TAB_MINI_MODULE, mini_headers),
            "module_df": load_tab(TAB_MODULE, module_headers),
            "batch_df": load_tab(TAB_BATCH_FIBER, batch_headers),
            "uncoated_df": load_tab(TAB_UNCOATED_SPOOL, uncoated_headers),
            "coated_df": load_tab(TAB_COATED_SPOOL, coated_headers),
            "dcoating_df": load_tab(TAB_DCOATING, dcoating_headers),
        }
    except gspread.exceptions.APIError:
        st.error("Google Sheets API error (quota exceeded or unavailable). Please wait and try again.")
        return None

# --- Manual Data Refresh & Caching ---
def manual_refresh(force=False):
    last_refresh = st.session_state.get("last_refresh", 0)
    if not force and (time.time() - last_refresh < 60):
        st.warning("Please wait at least a minute between refreshes.")
        return
    with st.spinner("Loading data from Google Sheets..."):
        data = load_all_tab_data()
        if data is not None:
            st.session_state["tab_data"] = data
            st.session_state["last_refresh"] = time.time()
            st.session_state["refresh_time_str"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.success(f"Data loaded successfully! (as of {st.session_state['refresh_time_str']})")

# --- UI: Manual Refresh Button ---
st.button("🔄 Load/Refresh Data", on_click=manual_refresh)

if "tab_data" not in st.session_state:
    st.info("Click 'Load/Refresh Data' to load the latest info from Google Sheets.")
    st.stop()

tab_data = st.session_state["tab_data"]
mini_df = tab_data["mini_df"]
module_df = tab_data["module_df"]
batch_df = tab_data["batch_df"]
uncoated_df = tab_data["uncoated_df"]
coated_df = tab_data["coated_df"]
dcoating_df = tab_data["dcoating_df"]

# --- Selection/Dropdown data ---
mini_modules = module_df[module_df["Module Type"].str.lower() == "mini"]["Module ID"].tolist()
batch_ids = batch_df.get("Batch_Fiber_ID", pd.Series()).dropna().tolist()
uncoated_ids = uncoated_df.get("UncoatedSpool_ID", pd.Series()).dropna().tolist()
coated_ids = coated_df.get("CoatedSpool_ID", pd.Series()).dropna().tolist() if not coated_df.empty else []
dcoating_ids = dcoating_df.get("DCoating_ID", pd.Series()).dropna().tolist()

# --- Label generator ---
def generate_c_module_label(operator_initials):
    today = datetime.today().strftime("%Y%m%d")
    base = today + operator_initials.upper()
    labels = mini_df["Module Label"].dropna().tolist() if "Module Label" in mini_df else []
    existing = [l.replace(base, '') for l in labels if l.startswith(base)]
    next_letter = chr(ord(max(existing)) + 1) if existing else 'A'
    return base + next_letter

# --- Mini Module Form ---
st.title("🧪 Mini Module Entry Form")
st.caption(f"Last data refresh: {st.session_state.get('refresh_time_str', '-')}")
with st.form("mini_module_form", clear_on_submit=True):
    st.subheader("🔹 Mini Module Entry")

    selected_module = st.selectbox("Module ID (Mini only)", mini_modules)
    existing = mini_df[mini_df["Module ID"] == selected_module]
    prefill = existing.iloc[0] if not existing.empty else None

    mini_module_id = prefill["Mini Module ID"] if prefill is not None else f"MINIMOD-{str(len(mini_df)+1).zfill(3)}"
    st.markdown(f"**Mini Module ID:** `{mini_module_id}`")

    batch_fiber_id = st.selectbox("Batch_Fiber_ID", batch_ids, index=batch_ids.index(prefill["Batch_Fiber_ID"]) if prefill else 0)
    uncoated_spool_id = st.selectbox("UncoatedSpool_ID", uncoated_ids, index=uncoated_ids.index(prefill["UncoatedSpool_ID"]) if prefill else 0)
    if coated_ids:
        coated_spool_id = st.selectbox(
            "CoatedSpool_ID",
            coated_ids,
            index=coated_ids.index(prefill["CoatedSpool_ID"]) if prefill and prefill["CoatedSpool_ID"] in coated_ids else 0)
    else:
        st.warning("⚠️ No Coated Spool IDs found. Please add them to the 'Coated Spool Tbl' sheet.")
        coated_spool_id = ""
    dcoating_id = st.selectbox("DCoating_ID", dcoating_ids, index=dcoating_ids.index(prefill["DCoating_ID"]) if prefill and prefill["DCoating_ID"] in dcoating_ids else 0)

    num_fibers = st.number_input("Number of Fibers", step=1, value=int(prefill["Number of Fibers"]) if prefill else 0)
    fiber_length = st.number_input("Fiber Length (inches)", format="%.2f", value=float(prefill["Fiber Length"]) if prefill else 0.0)
    active_area = st.number_input("C - Active Area", format="%.2f", value=float(prefill["Active Area"]) if prefill else 0.0)
    operator_initials = st.text_input("Operator Initials", value=prefill["Operator Initials"] if prefill else "")
    auto_label = st.checkbox("Auto-generate C-Module Label?", value=True)
    module_label = generate_c_module_label(operator_initials) if auto_label and operator_initials else st.text_input("C-Module Label", value=prefill["Module Label"] if prefill else "")
    notes = st.text_area("Notes", value=prefill["Notes"] if prefill else "")
    date_val = st.date_input("Date", value=datetime.today().date() if prefill is None else datetime.strptime(str(prefill["Date"]), "%Y-%m-%d").date())
    submit = st.form_submit_button("💾 Save Entry")

# --- Save to Google Sheets on Submit ---
if submit:
    row = [
        mini_module_id, selected_module, batch_fiber_id, uncoated_spool_id,
        coated_spool_id, dcoating_id, num_fibers, fiber_length, active_area,
        operator_initials, module_label, notes, str(date_val)
    ]
    try:
        gc = get_gsheet_client()
        sh = gc.open(GOOGLE_SHEET_NAME)
        ws = sh.worksheet(TAB_MINI_MODULE)
        if prefill is not None:
            idx = mini_df[mini_df["Mini Module ID"] == mini_module_id].index[0] + 2
            ws.delete_rows(idx)
            time.sleep(1)
            ws.insert_row(row, idx)
            st.success("✅ Entry updated.")
        else:
            ws.append_row(row)
            st.success("✅ Entry saved.")
        time.sleep(1)
        manual_refresh(force=True)
    except gspread.exceptions.APIError:
        st.error("Google Sheets API error on save. Try again in a minute.")
    except Exception as e:
        st.error(f"❌ Error saving: {e}")

# --- Recent (Last 7 Days) ---
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
