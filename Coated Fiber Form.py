# === IMPORTS ===
import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# Setup
def get_or_create_worksheet(sheet, title, headers):
    try:
        worksheet = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=title, rows="1000", cols="50")
        worksheet.append_row(headers)
    return worksheet

def get_next_id(worksheet, id_column):
    records = worksheet.get_all_records()
    if records:
        last_id = max([int(record[id_column]) for record in records if str(record.get(id_column, '')).isdigit()])
        return last_id + 1
    else:
        return 1

# === STREAMLIT SETUP ===
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
spreadsheet = client.open("R&D Data Form")

# ------------------ Coated Spool Tbl ------------------ #
st.header("Coated Spool Entry")
cs_headers = ["CoatedSpool_ID", "UnCoatedSpool_ID", "Date"]
cs_sheet = get_or_create_worksheet(spreadsheet, "Coated Spool Tbl", cs_headers)

uncoated_sheet = get_or_create_worksheet(spreadsheet, "UnCoatedSpool ID Tbl", ["UnCoatedSpool_ID", "Type", "C_Length"])
uncoated_df = pd.DataFrame(uncoated_sheet.get_all_records())
cs_df = pd.DataFrame(cs_sheet.get_all_records())

uncoated_df.columns = uncoated_df.columns.str.strip()
cs_df.columns = cs_df.columns.str.strip()

# Show current ID to be created
next_id = get_next_id(cs_sheet, "CoatedSpool_ID")
st.markdown(f"**Next CoatedSpool_ID will be:** `{next_id}`")

# All available IDs labeled with usage
used_ids = set(cs_df["UnCoatedSpool_ID"].astype(str)) if not cs_df.empty and "UnCoatedSpool_ID" in cs_df.columns else set()
uncoated_choices = []
if "UnCoatedSpool_ID" in uncoated_df.columns:
    for _, row in uncoated_df.iterrows():
        try:
            uid = str(row["UnCoatedSpool_ID"]).strip()
            label = f"{uid} ({'used' if uid in used_ids else 'not used'})"
            uncoated_choices.append((label, uid))
        except KeyError:
            continue

with st.form("Coated Spool Form"):
    if uncoated_choices:
        display_labels = [label for label, _ in uncoated_choices]
        selected_label = st.selectbox("UnCoatedSpool_ID", display_labels)
        selected_id = dict(uncoated_choices)[selected_label]
        submitted = st.form_submit_button("Submit")
        if submitted:
            cs_sheet.append_row([next_id, selected_id, datetime.today().strftime("%Y-%m-%d")])
            st.success(f"Coated Spool with ID {next_id} submitted successfully!")
    else:
        st.warning("No UnCoatedSpool_IDs found. Please add a new entry in the 'UnCoatedSpool ID Tbl' sheet.")

# Show last 7 days
st.subheader("Recent Coated Spool Entries")
if not cs_df.empty and "Date" in cs_df.columns:
    cs_df["Date"] = pd.to_datetime(cs_df["Date"], errors="coerce")
    last_7 = cs_df[cs_df["Date"] >= datetime.today() - pd.Timedelta(days=7)]
    if not last_7.empty:
        st.dataframe(last_7)
    else:
        st.info("No recent Coated Spool entries in the last 7 days.")
else:
    st.info("No records or missing Date column in Coated Spool Tbl.")

# === FIBER PER COATING RUN FORM ===
st.header("Fiber Per Coating Run Entry")
fpcr_headers = [
    "FiberCoat_ID", "PCoating_ID", "CoatedSpool_ID",
    "Payout_Position", "Length_Coated", "Label", "Notes", "Date"
]
fpcr_sheet = get_or_create_worksheet(sheet, "Fiber per Coating Run Tbl (Coating)", fpcr_headers)

pcoating_sheet = get_or_create_worksheet(sheet, "Pilot Coating Process Tbl", ["PCoating ID"])
pcoating_records = pcoating_sheet.get_all_records()
pcoating_ids = [str(r.get("PCoating ID", "")).strip() for r in pcoating_records if r.get("PCoating ID")]

coated_records = cs_sheet.get_all_records()
coated_ids = [str(r.get("CoatedSpool_ID", "")).strip() for r in coated_records if r.get("CoatedSpool_ID")]

with st.form("Fiber Per Coating Run Form"):
    if pcoating_ids and coated_ids:
        pcoating_selected = st.selectbox("PCoating ID", pcoating_ids)
        coated_selected = st.selectbox("CoatedSpool ID", coated_ids)
        payout_pos = st.text_input("Payout Position")
        length_coated = st.number_input("Length Coated (m)", min_value=0.0)
        label = st.text_input("Label")
        notes = st.text_area("Notes")
        fpcr_submit = st.form_submit_button("Submit")
        if fpcr_submit:
            fibercoat_id = get_next_id(fpcr_sheet, "FiberCoat_ID")
            fpcr_sheet.append_row([
                fibercoat_id, pcoating_selected, coated_selected,
                payout_pos, length_coated, label, notes, datetime.today().strftime("%Y-%m-%d")
            ])
            st.success(f"✅ FiberCoat ID {fibercoat_id} submitted.")
    else:
        st.warning("Ensure both PCoating IDs and Coated Spool IDs are available.")

# Show last 7 days
st.subheader("Recent Fiber Coating Runs")
recent_fpcr = get_last_7_days_df(fpcr_sheet, "Date")
if not recent_fpcr.empty:
    st.dataframe(recent_fpcr)
else:
    st.info("No recent fiber coating entries in the last 7 days.")
