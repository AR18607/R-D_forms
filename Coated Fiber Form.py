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
        last_id = max([int(r[id_column]) for r in records if str(r.get(id_column, '')).isdigit()])
        return last_id + 1
    return 1

def get_last_7_days_df(ws, date_col_name):
    df = pd.DataFrame(ws.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip()
        if date_col_name in df.columns:
            df[date_col_name] = pd.to_datetime(df[date_col_name], errors="coerce")
            return df[df[date_col_name] >= datetime.today() - timedelta(days=7)]
    return pd.DataFrame()

# === COATED SPOOL FORM ===
st.header("Coated Spool Entry")
cs_headers = ["CoatedSpool_ID", "UnCoatedSpool_ID", "Date"]
cs_sheet = get_or_create_worksheet(sheet, "Coated Spool Tbl", cs_headers)

uncoated_sheet = get_or_create_worksheet(sheet, "UnCoatedSpool ID Tbl", ["UncoatedSpool_ID", "Type", "C_Length", "Date_Time"])
uncoated_df = pd.DataFrame(uncoated_sheet.get_all_records())
uncoated_df.columns = uncoated_df.columns.str.strip()

used_uncoated = set(str(uid).strip() for uid in cs_sheet.col_values(2)[1:] if uid.strip())

with st.form("coated_spool_form"):
    next_cs_id = get_next_id(cs_sheet, "CoatedSpool_ID")
    st.markdown(f"**Next CoatedSpool_ID:** `{next_cs_id}`")

    uncoated_choices = []
    if not uncoated_df.empty and "UncoatedSpool_ID" in uncoated_df.columns:
        for _, row in uncoated_df.iterrows():
            uid = str(row["UncoatedSpool_ID"]).strip()
            tag = "used" if uid in used_uncoated else "not used"
            label = f"{uid} - {row['Type']} - {row['C_Length']}m ({tag})"
            uncoated_choices.append((label, uid))

    if uncoated_choices:
        options = [label for label, _ in uncoated_choices]
        selected_label = st.selectbox("Select UnCoatedSpool_ID", options)
        uncoated_selected = dict(uncoated_choices)[selected_label]

        create_new = st.radio("Do you want to create a new UnCoatedSpool_ID?", ["No", "Yes"])
        cs_submit = st.form_submit_button("Submit")

        if cs_submit:
            if create_new == "No":
                cs_sheet.append_row([next_cs_id, uncoated_selected, datetime.today().strftime("%Y-%m-%d")])
                st.success(f"✅ Coated Spool ID {next_cs_id} submitted.")
            else:
                st.warning("Please scroll down to create a new UnCoatedSpool_ID entry.")
    else:
        st.warning("No existing UnCoatedSpool_ID entries found.")
        st.form_submit_button("Submit (disabled)", disabled=True)

# === CREATE NEW UNCOATED SPOOL ENTRY ===
st.markdown("---")
st.subheader("Create New UnCoatedSpool_ID Entry")

with st.form("create_uncoated_form"):
    new_id = get_next_id(uncoated_sheet, "UncoatedSpool_ID")
    st.markdown(f"**Next UnCoatedSpool_ID:** `{new_id}`")
    new_type = st.text_input("Type")
    new_length = st.number_input("C_Length (m)", min_value=0.0)
    new_submit = st.form_submit_button("Create UnCoatedSpool_ID")

    if new_submit:
        uncoated_sheet.append_row([new_id, new_type, new_length, datetime.today().strftime("%Y-%m-%d %H:%M:%S")])
        st.success(f"✅ New UnCoatedSpool_ID {new_id} created. You can now use it in the dropdown above.")

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
