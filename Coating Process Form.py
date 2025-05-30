import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd

# ---------- CONFIG ----------
SHEET_NAME = "R&D Data Form"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(st.secrets["gcp_service_account"]), scope
)
client = gspread.authorize(creds)
spreadsheet = client.open(SHEET_NAME)

def get_or_create_worksheet(title, headers):
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows="1000", cols="50")
        ws.append_row(headers)
    return ws

@st.cache_data(ttl=600)  # Cache data for 10 minutes to reduce API calls
def get_all_records_cached(ws):
    return ws.get_all_records()

def get_next_id(ws, prefix):
    rows = ws.get_all_values()[1:]  # skip header row
    ids = [row[0] for row in rows if row and row[0].startswith(prefix)]
    nums = [int(i.split('-')[-1]) for i in ids if i.split('-')[-1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

def filter_last_7_days(df, date_col):
    today = datetime.today()
    def is_recent(x):
        try:
            d = pd.to_datetime(x)
            return d.date() >= (today - timedelta(days=7)).date()
        except:
            return False
    return df[df[date_col].apply(is_recent)] if date_col in df.columns else df.iloc[[]]

# ---------------- Worksheets ----------------
solution_ws = get_or_create_worksheet("Solution ID Tbl", ["Solution ID", "Type", "Expired", "Consumed"])
pcoat_ws = get_or_create_worksheet("Pilot Coating Process Tbl", [
    "PCoating ID", "Solution ID", "Date", "Box Temperature", "Box RH", "N2 flow",
    "Load cell slope", "Number of fibers", "Coating Speed", "Tower 1 set point", "Tower 1 entry temperature",
    "Tower 2 set point", "Tower 2 entry temperature", "Coating Layer Type", "Operator Initials", "Ambient Temp",
    "Ambient %RH", "Notes"
])
tension_ws = get_or_create_worksheet("Coater Tension Tbl", [
    "Tension ID", "PCoating ID", "Payout Location", "Tension (g)", "Notes"
])
dcoat_ws = get_or_create_worksheet("Dip Coating Process Tbl", [
    "DCoating ID", "Solution ID", "Batch Fiber ID", "UncoatedSpool ID", "Date", "Box Temperature", "Box RH",
    "N2 flow", "Number of fibers", "Coating Speed", "Annealing Time", "Annealing Temperature",
    "Coating Layer Type", "Operator Initials", "Ambient Temp", "Ambient %RH", "Notes"
])
mass_ws = get_or_create_worksheet("Coating Solution Mass Tbl", [
    "SolutionMass ID", "Solution ID", "Date & Time", "DCoating ID", "PCoating ID",
    "Solution Mass", "Operators Initials", "Notes"
])

# ---------------- Dropdown data ----------------
solution_ids = [r["Solution ID"] for r in get_all_records_cached(solution_ws)]
pcoat_ids = [r["PCoating ID"] for r in get_all_records_cached(pcoat_ws)]
dcoat_ids = [r["DCoating ID"] for r in get_all_records_cached(dcoat_ws)]
payout_locations = ["A", "B", "C", "D", "Other"]

# ---------------- Streamlit UI ----------------
st.title("🧪 Coating Process Form")

tab1, tab2, tab3 = st.tabs(["Pilot Coating", "Coater Tension", "Solution Mass"])

# Pilot Coating Form
with tab1:
    st.subheader("Pilot Coating Process Entry")
    with st.form("pilot_coating_form", clear_on_submit=True):
        next_pcoat_id = get_next_id(pcoat_ws, "PCOAT")
        st.markdown(f"**Auto-generated PCoating ID:** `{next_pcoat_id}`")
        pcoat_sol = st.selectbox("Solution ID", solution_ids, key="pilot_sol")
        pcoat_date = st.date_input("Date")
        box_temp = st.number_input("Box Temperature (°C)", min_value=0.0)
        box_rh = st.number_input("Box RH (%)", min_value=0.0)
        n2 = st.number_input("N2 flow", min_value=0.0)
        load_cell = st.number_input("Load cell slope", min_value=0.0)
        num_fibers = st.number_input("Number of fibers", min_value=0)
        coat_speed = st.number_input("Coating Speed", min_value=0.0)
        tower1 = st.number_input("Tower 1 set point", min_value=0.0)
        tower1_ent = st.number_input("Tower 1 entry temperature", min_value=0.0)
        tower2 = st.number_input("Tower 2 set point", min_value=0.0)
        tower2_ent = st.number_input("Tower 2 entry temperature", min_value=0.0)
        layer_type = st.selectbox("Coating Layer Type", ["GL", "AL", "PL"])
        op_init = st.text_input("Operator Initials")
        amb_temp = st.number_input("Ambient Temp", min_value=0.0)
        amb_rh = st.number_input("Ambient %RH", min_value=0.0)
        notes = st.text_area("Notes")
        pilot_submit = st.form_submit_button("Submit Pilot Coating Entry")
    if pilot_submit:
        pcoat_ws.append_row([
            next_pcoat_id, pcoat_sol, pcoat_date.strftime("%Y-%m-%d"), box_temp, box_rh, n2, load_cell, num_fibers, coat_speed,
            tower1, tower1_ent, tower2, tower2_ent, layer_type, op_init, amb_temp, amb_rh, notes
        ])
        st.success(f"Saved Pilot Coating Entry: {next_pcoat_id}")

    # 7-Day review
    try:
        pcoat_df = pd.DataFrame(get_all_records_cached(pcoat_ws))
        recent = filter_last_7_days(pcoat_df, "Date")
        st.markdown("### 📅 7-Day Review")
        st.dataframe(recent if not recent.empty else pd.DataFrame(columns=pcoat_df.columns))
    except Exception as e:
        st.error(f"Error loading Pilot Coating review: {e}")

# Coater Tension Form (multi-entry)
with tab2:
    st.subheader("Coater Tension Entry (Multi-Measurement)")
    if "tension_points" not in st.session_state:
        st.session_state.tension_points = []
    with st.form("tension_form", clear_on_submit=True):
        next_tension_id = get_next_id(tension_ws, "TENSION")
        st.markdown(f"**Auto-generated Tension ID:** `{next_tension_id}`")
        t_pcoat_id = st.selectbox("PCoating ID", pcoat_ids, key="tens_pcoat")
        payout_loc = st.selectbox("Payout Location", payout_locations, key="tens_payout")
        tension_val = st.number_input("Tension (g)", min_value=0.0)
        tension_note = st.text_area("Notes", key="tens_note")
        add_tension = st.form_submit_button("➕ Add Data Point")
    if add_tension:
        st.session_state.tension_points.append({
            "Tension ID": next_tension_id,
            "PCoating ID": t_pcoat_id,
            "Payout Location": payout_loc,
            "Tension (g)": tension_val,
            "Notes": tension_note
        })
    if st.session_state.tension_points:
        st.write("#### Pending Data Points")
        st.table(pd.DataFrame(st.session_state.tension_points))
        if st.button("Submit All Tension Data", key="submit_all_tension"):
            for entry in st.session_state.tension_points:
                tension_ws.append_row([
                    entry["Tension ID"], entry["PCoating ID"], entry["Payout Location"], entry["Tension (g)"], entry["Notes"]
                ])
            st.session_state.tension_points.clear()
            st.success("All tension entries saved!")
    # 7-day review
    try:
        tens_df = pd.DataFrame(get_all_records_cached(tension_ws))
        recent = filter_last_7_days(tens_df, "Tension ID")  # Change to date column if available
        st.markdown("### 📅 7-Day Review")
        st.dataframe(recent if not recent.empty else pd.DataFrame(columns=tens_df.columns))
    except Exception as e:
        st.error(f"Error loading Tension review: {e}")

# Coating Solution Mass Form (multi-entry)
with tab3:
    st.subheader("Coating Solution Mass Entry (Multi-Entry)")
    if "mass_points" not in st.session_state:
        st.session_state.mass_points = []
    with st.form("mass_form", clear_on_submit=True):
        next_mass_id = get_next_id(mass_ws, "SOLMASS")
        st.markdown(f"**Auto-generated SolutionMass ID:** `{next_mass_id}`")
        mass_sol = st.selectbox("Solution ID", solution_ids, key="mass_sol")
        mass_dt = st.date_input("Date", value=datetime.now())
        mass_tm = st.time_input("Time", value=datetime.now().time())
        mass_dcoat = st.selectbox("DCoating ID (optional)", [""] + dcoat_ids, key="mass_dcoat")
        mass_pcoat = st.selectbox("Pcoating ID", pcoat_ids, key="mass_pcoat")
        mass_val = st.number_input("Solution Mass", min_value=0.0, key="mass_val")
        mass_op = st.text_input("Operators Initials", key="mass_op")
        mass_note = st.text_area("Notes", key="mass_note")
        add_mass = st.form_submit_button("➕ Add Solution Mass Entry")
    if add_mass:
        dt_combined = datetime.combine(mass_dt, mass_tm)
        st.session_state.mass_points.append({
            "SolutionMass ID": next_mass_id,
            "Solution ID": mass_sol,
            "Date & Time": dt_combined.strftime("%Y-%m-%d %H:%M"),
            "DCoating ID": mass_dcoat,
            "Pcoating ID": mass_pcoat,
            "Solution Mass": mass_val,
            "Operators Initials": mass_op,
            "Notes": mass_note
        })
    if st.session_state.mass_points:
        st.write("#### Pending Solution Mass Entries")
        st.table(pd.DataFrame(st.session_state.mass_points))
        if st.button("Submit All Mass Data", key="submit_all_mass"):
            for entry in st.session_state.mass_points:
                mass_ws.append_row([
                    entry["SolutionMass ID"], entry["Solution ID"], entry["Date & Time"], entry["DCoating ID"],
                    entry["Pcoating ID"], entry["Solution Mass"], entry["Operators Initials"], entry["Notes"]
                ])
            st.session_state.mass_points.clear()
            st.success("All solution mass entries saved!")
    # 7-day review
    try:
        mass_df = pd.DataFrame(get_all_records_cached(mass_ws))
        recent = filter_last_7_days(mass_df, "Date & Time")
        st.markdown("### 📅 7-Day Review")
        st.dataframe(recent if not recent.empty else pd.DataFrame(columns=mass_df.columns))
    except Exception as e:
        st.error(f"Error loading Solution Mass review: {e}")
