# === IMPORTS ===
import json
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd

# === DISABLE ENTER KEY FORM SUBMIT ===
st.markdown("""
    <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    </script>
""", unsafe_allow_html=True)

# === GOOGLE SHEET SETUP ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
sheet = client.open("R&D Data Form")

# === HELPERS ===
def get_or_create_worksheet(sheet, title, headers):
    try:
        ws = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows="1000", cols="50")
        ws.append_row(headers)
    return ws

def get_next_id(worksheet, id_column):
    records = worksheet.get_all_records()
    if records:
        last_id = max([int(r[id_column]) for r in records if str(r[id_column]).isdigit()])
        return last_id + 1
    return 1

def get_last_7_days_df(ws, date_col_name):
    df = pd.DataFrame(ws.get_all_records())
    if date_col_name in df.columns:
        df[date_col_name] = pd.to_datetime(df[date_col_name], errors="coerce")
        return df[df[date_col_name] >= datetime.today() - timedelta(days=7)]
    return pd.DataFrame()

# === COATED SPOOL FORM ===
st.header("Coated Spool Entry")
cs_headers = ["CoatedSpool_ID", "UnCoatedSpool_ID"]
cs_sheet = get_or_create_worksheet(sheet, "Coated Spool Tbl", cs_headers)

uncoated_sheet = get_or_create_worksheet(sheet, "UnCoatedSpool ID Tbl", ["UncoatedSpool_ID", "Type", "C_Length"])
uncoated_ids = [str(r["UncoatedSpool_ID"]) for r in uncoated_sheet.get_all_records()]

with st.form("Coated Spool Form"):
    uncoated_selected = st.selectbox("UnCoatedSpool ID", uncoated_ids)
    cs_submit = st.form_submit_button("Submit")
    if cs_submit:
        cs_id = get_next_id(cs_sheet, "CoatedSpool_ID")
        cs_sheet.append_row([cs_id, uncoated_selected])
        st.success(f"✅ Coated Spool ID {cs_id} submitted.")

# Show last 7 days
st.subheader("Recent Coated Spool Entries")
recent_cs = get_last_7_days_df(cs_sheet, "Date")
if not recent_cs.empty:
    st.dataframe(recent_cs)
else:
    st.info("No recent Coated Spool entries in the last 7 days.")

# === FIBER PER COATING RUN FORM ===
st.header("Fiber Per Coating Run Entry")
fpcr_headers = [
    "FiberCoat_ID", "PCoating_ID", "CoatedSpool_ID",
    "Payout_Position", "Length_Coated", "Label", "Notes", "Date"
]
fpcr_sheet = get_or_create_worksheet(sheet, "Fiber per Coating Run Tbl (Coating)", fpcr_headers)

pcoating_sheet = get_or_create_worksheet(sheet, "Pilot Coating Process Tbl", ["PCoating ID"])
pcoating_ids = [str(r["PCoating ID"]) for r in pcoating_sheet.get_all_records()]
coated_ids = [str(r["CoatedSpool_ID"]) for r in cs_sheet.get_all_records()]

with st.form("Fiber Per Coating Run Form"):
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

# Show last 7 days
st.subheader("Recent Fiber Coating Runs")
recent_fpcr = get_last_7_days_df(fpcr_sheet, "Date")
if not recent_fpcr.empty:
    st.dataframe(recent_fpcr)
else:
    st.info("No recent fiber coating entries in the last 7 days.")
