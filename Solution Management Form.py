# --- Complete Streamlit Solution Management Form Implementation with All Enhancements ---

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import time

# --- Configuration ---
SPREADSHEET_KEY = "1uPdUWiiwMdJCYJaxZ5TneFa9h6tbSrs327BVLT5GVPY"
SOLUTION_ID_HEADERS = ["Solution ID", "Type", "Expired", "Consumed"]
PREP_HEADERS = [
    "Solution Prep ID", "Solution ID (FK)", "Desired Solution Concentration", "Desired Final Volume (ml)",
    "Solvent", "Solvent Lot Number", "Solvent Weight Measured (g)", "Polymer",
    "Polymer starting concentration", "Polymer Lot Number", "Polymer Weight Measured (g)",
    "Prep Date", "Initials", "Notes", "C-Solution Concentration", "C-Label for jar"
]
COMBINED_HEADERS = [
    "Combined Solution ID", "Solution ID A", "Solution ID B",
    "Solution Mass A", "Solution Mass B", "Date", "Initials", "Notes"
]

# --- Google Sheets Utility Functions ---
@st.cache_resource(ttl=600)
def connect_google_sheet(sheet_key):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_key)

def retry_open_worksheet(spreadsheet, tab_name, retries=3, wait=2):
    for i in range(retries):
        try:
            return spreadsheet.worksheet(tab_name)
        except gspread.exceptions.APIError as e:
            if i < retries - 1:
                time.sleep(wait)
            else:
                st.error(f":rotating_light: API Error while accessing `{tab_name}`: {str(e)}")
                st.stop()

def get_or_create_tab(spreadsheet, tab_name, headers):
    try:
        worksheet = retry_open_worksheet(spreadsheet, tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="50")
        worksheet.insert_row(headers, 1)
    return worksheet

@st.cache_data(ttl=120)
def cached_get_all_records(sheet_key, tab_name):
    spreadsheet = connect_google_sheet(sheet_key)
    worksheet = retry_open_worksheet(spreadsheet, tab_name)
    return worksheet.get_all_records()

# --- Initialize Sheets ---
spreadsheet = connect_google_sheet(SPREADSHEET_KEY)
solution_sheet = get_or_create_tab(spreadsheet, "Solution ID Tbl", SOLUTION_ID_HEADERS)
prep_sheet = get_or_create_tab(spreadsheet, "Solution Prep Data Tbl", PREP_HEADERS)
combined_sheet = get_or_create_tab(spreadsheet, "Combined Solution Tbl", COMBINED_HEADERS)

# --- Main Form Title ---
st.markdown("# :page_facing_up: **Solution Management Form**")

# --- Solution ID Management ---
st.markdown("## :small_blue_diamond: Solution ID Entry")
existing_solution_records = cached_get_all_records(SPREADSHEET_KEY, "Solution ID Tbl")
solution_df = pd.DataFrame(existing_solution_records)

new_solution_id = f"SOL-{str(len(solution_df)+1).zfill(3)}"
st.markdown(f"**Auto-generated Solution ID:** `{new_solution_id}`")

with st.form("new_solution_id_form"):
    solution_type = st.selectbox("Type", ["New", "Combined"])
    expired = st.selectbox("Expired?", ["No", "Yes"], index=0)
    consumed = st.selectbox("Consumed?", ["No", "Yes"], index=0)
    submit_solution = st.form_submit_button("Submit New Solution ID")

if submit_solution:
    solution_sheet.append_row([new_solution_id, solution_type, expired, consumed])
    st.success(":white_check_mark: New Solution ID saved!")

st.checkbox("View/Update Existing Solution IDs")
if st.session_state.get('View/Update Existing Solution IDs'):
    for idx, row in solution_df.iterrows():
        col1, col2 = st.columns(2)
        expired_update = col1.checkbox(f"Expired - {row['Solution ID']}", value=row['Expired'] == "Yes")
        consumed_update = col2.checkbox(f"Consumed - {row['Solution ID']}", value=row['Consumed'] == "Yes")
        if expired_update != (row['Expired'] == "Yes") or consumed_update != (row['Consumed'] == "Yes"):
            solution_sheet.update_cell(idx + 2, 3, "Yes" if expired_update else "No")
            solution_sheet.update_cell(idx + 2, 4, "Yes" if consumed_update else "No")
            st.success(f"Updated {row['Solution ID']} status.")

# --- Solution Prep Data Entry ---
st.markdown("## :small_blue_diamond: Solution Prep Data Entry")
valid_solution_ids = solution_df[(solution_df['Type'] != "Combined") & (solution_df['Expired'] != "Yes")]["Solution ID"]
selected_solution_fk = st.selectbox("Select Solution ID", options=valid_solution_ids.tolist())

with st.form("solution_prep_form"):
    desired_conc = st.number_input("Desired Solution Concentration (%)", format="%.2f")
    final_volume_ml = st.number_input("Desired Final Volume (ml)", format="%.1f")
    solvent_weight = st.number_input("Solvent Weight Measured (g)", format="%.2f")
    polymer_weight = st.number_input("Polymer Weight Measured (g)", format="%.2f")

    total_weight = polymer_weight + solvent_weight
    c_sol_conc = (polymer_weight / total_weight) if total_weight else 0
    st.markdown(f"**C-Solution Concentration:** `{c_sol_conc:.4f}`")

    submit_prep = st.form_submit_button("Submit Solution Prep Data")

if submit_prep:
    prep_id = f"PREP-{str(len(prep_sheet.get_all_records())+1).zfill(3)}"
    prep_sheet.append_row([prep_id, selected_solution_fk, desired_conc, final_volume_ml, "", "", solvent_weight, "", 0, "", polymer_weight, str(datetime.today().date()), "", "", c_sol_conc, ""])
    st.success(":white_check_mark: Solution Prep Data saved!")

# --- Combined Solution Entry ---
st.markdown("## :small_blue_diamond: Combined Solution Entry")
valid_combined_ids = solution_df[(solution_df["Type"] == "Combined") & (solution_df["Expired"] != "Yes")]["Solution ID"]
selected_combined_id = st.selectbox("Select Combined Solution ID", options=valid_combined_ids.tolist())

st.markdown("### Select Solutions to Combine")
solution_options = solution_df[(solution_df["Expired"] == "No") & (solution_df["Consumed"] == "No")]["Solution ID"].tolist()

solution_a = st.selectbox("Solution ID A", options=solution_options)
solution_b = st.selectbox("Solution ID B", options=solution_options)

combined_conc = "Calculation Pending"
st.markdown(f"**Combined Solution Concentration:** `{combined_conc}`")

# Disable Enter submission
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# --- Last 7 Days Data ---
st.markdown("## 📅 Last 7 Days Data Preview")
recent_prep_df = pd.DataFrame(prep_sheet.get_all_records())
recent_prep_df["Prep Date"] = pd.to_datetime(recent_prep_df["Prep Date"])
st.dataframe(recent_prep_df[recent_prep_df["Prep Date"] >= datetime.today() - timedelta(days=7)])
