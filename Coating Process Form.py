import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd

# --------- Google Sheets Setup ------------
SHEET_NAME = "R&D Data Form"
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
spreadsheet = client.open(SHEET_NAME)

def get_or_create_worksheet(title, headers):
    try:
        ws = spreadsheet.worksheet(title)
        # Check and fix headers if needed
        current_headers = ws.row_values(1)
        if current_headers != headers:
            ws.delete_rows(1)
            ws.insert_row(headers, 1)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows="1000", cols="50")
        ws.insert_row(headers, 1)
    return ws

def get_last_id(ws, prefix):
    vals = ws.col_values(1)[1:]
    nums = [int(v.split('-')[-1]) for v in vals if v.startswith(prefix)]
    next_id = max(nums)+1 if nums else 1
    return f"{prefix}-{str(next_id).zfill(3)}"

def filter_7_days(records, date_col):
    today = datetime.now()
    filtered = []
    for r in records:
        dt_str = r.get(date_col, '')
        try:
            if len(dt_str) > 10:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
            if dt.date() >= (today.date() - timedelta(days=7)):
                filtered.append(r)
        except:
            continue
    return filtered

# --------- Table Setup ----------
# Main tabs/worksheets
PCP_HEADERS = ["PCoating ID","Solution ID","Date","Box Temperature","Box RH","N2 flow",
               "Load cell slope","Number of fibers","Coating Speed","Tower 1 set point",
               "Tower 1 entry temperature","Tower 2 set point","Tower 2 entry temperature",
               "Coating Layer Type (GL/AL/PL)","Operator Initials","Ambient Temp","Ambient %RH","Notes"]

CT_HEADERS = ["Tension ID","PCoating ID","Payout Location","Tension (g)","Notes"]

CSM_HEADERS = ["SolutionMass ID","Solution ID","Date & Time","DCoating ID","Pcoating ID",
               "Solution Mass","Operators Initials","Notes"]

pcp_ws = get_or_create_worksheet("Pilot Coating Process Tbl", PCP_HEADERS)
ct_ws  = get_or_create_worksheet("Coater Tension Tbl", CT_HEADERS)
csm_ws = get_or_create_worksheet("Coating Solution Mass Tbl", CSM_HEADERS)

# FKs: Load lists for dropdowns
solution_ids = list(set([r.get("Solution ID") for r in pcp_ws.get_all_records()] +
                        [r.get("Solution ID") for r in csm_ws.get_all_records()]))
solution_ids = [s for s in solution_ids if s] or ["SOL-001"]

pcoating_ids = [r.get("PCoating ID") for r in pcp_ws.get_all_records() if r.get("PCoating ID")]
dcoating_ids = [r.get("DCoating ID") for r in csm_ws.get_all_records() if r.get("DCoating ID")]

payout_locations = ["Entry", "Exit", "Middle"]

st.title("🧪 Coating Process Form")

tabs = st.tabs(["Pilot Coating", "Coater Tension", "Coating Solution Mass"])

# ----------------- Pilot Coating Process Tab -----------------
with tabs[0]:
    st.header("Pilot Coating Process Entry")
    pcoat_id = get_last_id(pcp_ws, "PCOAT")
    st.markdown(f"**Auto-generated PCoating ID:** <span style='color:purple'>{pcoat_id}</span>", unsafe_allow_html=True)
    with st.form("pilot_form", clear_on_submit=True):
        sol_id = st.selectbox("Solution ID", solution_ids)
        date = st.date_input("Date", datetime.today())
        box_temp = st.number_input("Box Temperature (°C)", 0.0)
        box_rh = st.number_input("Box RH (%)", 0.0)
        n2_flow = st.number_input("N2 flow", 0.0)
        load_slope = st.number_input("Load cell slope", 0.0)
        n_fibers = st.number_input("Number of fibers", 0)
        coat_speed = st.number_input("Coating Speed", 0.0)
        t1_set = st.number_input("Tower 1 set point", 0.0)
        t1_entry = st.number_input("Tower 1 entry temperature", 0.0)
        t2_set = st.number_input("Tower 2 set point", 0.0)
        t2_entry = st.number_input("Tower 2 entry temperature", 0.0)
        layer = st.selectbox("Coating Layer Type (GL/AL/PL)", ["GL","AL","PL"])
        op_init = st.text_input("Operator Initials")
        amb_temp = st.number_input("Ambient Temp", 0.0)
        amb_rh = st.number_input("Ambient %RH", 0.0)
        notes = st.text_area("Notes")
        pilot_submit = st.form_submit_button("💾 Submit Pilot Coating Entry")
    if pilot_submit:
        try:
            pcp_ws.append_row([
                pcoat_id, sol_id, date.strftime("%Y-%m-%d"), box_temp, box_rh, n2_flow,
                load_slope, n_fibers, coat_speed, t1_set, t1_entry, t2_set, t2_entry,
                layer, op_init, amb_temp, amb_rh, notes
            ])
            st.success(f"✅ Saved: {pcoat_id}")
        except Exception as e:
            st.error(f"Failed to save: {e}")

# ----------------- Coater Tension Tab -----------------
with tabs[1]:
    st.header("Coater Tension Entry (Multi-Entry)")
    t_pcoat_ids = [x for x in pcoating_ids] or ["PCOAT-001"]
    if "ct_multi" not in st.session_state: st.session_state.ct_multi = []
    ct_pid = st.selectbox("Pcoating ID", t_pcoat_ids)
    payout = st.selectbox("Payout Location", payout_locations)
    tension = st.number_input("Tension (g)", 0.0)
    ct_notes = st.text_area("Notes (Memo)")
    if st.button("➕ Add Tension Row"):
        tid = get_last_id(ct_ws, "TENSION")
        st.session_state.ct_multi.append([tid, ct_pid, payout, tension, ct_notes])
    if st.session_state.ct_multi:
        st.dataframe(pd.DataFrame(st.session_state.ct_multi, columns=CT_HEADERS))
        if st.button("Submit All Tension Rows"):
            for row in st.session_state.ct_multi:
                ct_ws.append_row(row)
            st.success("✅ All tension entries saved!")
            st.session_state.ct_multi = []

# ----------------- Coating Solution Mass Tab -----------------
with tabs[2]:
    st.header("Coating Solution Mass Entry (Multi-Entry)")
    mass_sol_id = st.selectbox("Solution ID", solution_ids)
    mass_date = st.date_input("Date", datetime.today())
    mass_time = st.time_input("Time", datetime.now().time())
    dt = datetime.combine(mass_date, mass_time)
    mass_dcoating_id = st.selectbox("DCoating ID", [""] + dcoating_ids)
    mass_pcoating_id = st.selectbox("Pcoating ID", pcoating_ids)
    mass_val = st.number_input("Solution Mass", 0.0)
    mass_op_init = st.text_input("Operators Initials")
    mass_notes = st.text_area("Notes")
    if "mass_multi" not in st.session_state: st.session_state.mass_multi = []
    if st.button("➕ Add Solution Mass Row"):
        mid = get_last_id(csm_ws, "CSM")
        st.session_state.mass_multi.append([
            mid, mass_sol_id, dt.strftime("%Y-%m-%d %H:%M"),
            mass_dcoating_id, mass_pcoating_id,
            mass_val, mass_op_init, mass_notes
        ])
    if st.session_state.mass_multi:
        st.dataframe(pd.DataFrame(st.session_state.mass_multi, columns=CSM_HEADERS))
        if st.button("Submit All Mass Rows"):
            for row in st.session_state.mass_multi:
                csm_ws.append_row(row)
            st.success("✅ All mass entries saved!")
            st.session_state.mass_multi = []

# ----------------- 7-Day Review Section -----------------
st.markdown("## 📅 7-Day Review (All Tables)")

def review_table(ws, title, date_col):
    st.markdown(f"#### {title}")
    try:
        records = ws.get_all_records()
        last7 = filter_7_days(records, date_col)
        if last7:
            st.dataframe(pd.DataFrame(last7))
        else:
            st.info("No entries in last 7 days.")
    except Exception as e:
        st.error(f"Could not load review table: {e}")

review_table(pcp_ws, "Pilot Coating Process Tbl", "Date")
review_table(ct_ws, "Coater Tension Tbl", "Tension ID")  # (change to Date if you have date)
review_table(csm_ws, "Coating Solution Mass Tbl", "Date & Time")
