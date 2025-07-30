import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta

# ========== MYSQL CONFIG ==============
db_config = {
    'user': 'root',
    'password': 'Ardenttechnologies@1',
    'host': 'localhost',
    'database': 'rnd_new_database'
}

def get_conn():
    return mysql.connector.connect(**db_config)

# -------- DB Utility Functions ----------
def fetch_df(query, params=None):
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute(query, params=None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    conn.commit()
    cursor.close()
    conn.close()

def get_next_id(table, prefix, id_col):
    df = fetch_df(f"SELECT {id_col} FROM {table}")
    ids = df[id_col].tolist()
    nums = [int(str(x).split('-')[-1]) for x in ids if isinstance(x, str) and x.startswith(prefix) and str(x).split('-')[-1].isdigit()]
    return f"{prefix}-{max(nums)+1:03d}" if nums else f"{prefix}-001"

# ------- Safe get for row dicts -------
def safe_get(row, key, default=""):
    if key in row:
        return row[key]
    for k in row:
        if k.strip().lower() == key.strip().lower():
            return row[k]
    return default

# ---------- APP STARTS ---------------

st.title("📄 Solution Management Form (MySQL Version)")
st.write("Full feature port: ID generation, editing, table filtering, auto-calculation, dynamic dropdowns.")

# 1. LOAD DATA
solution_df = fetch_df("SELECT * FROM solution_id_tbl")
prep_df = fetch_df("SELECT * FROM solution_prep_data_tbl")
comb_df = fetch_df("SELECT * FROM combined_solution_tbl")

# ========== 1. SOLUTION ID TABLE ===========
st.header("🔹 Solution ID Entry / Management")

with st.expander("View / Update Existing Solution IDs", expanded=False):
    if not solution_df.empty:
        edit_id = st.selectbox("Select Solution ID to update", [""] + solution_df['solution_id'].tolist())
        if edit_id:
            row = solution_df.loc[solution_df['solution_id'] == edit_id].iloc[0]
            expired_val = st.selectbox("Expired?", ['No', 'Yes'], index=row['expired'], key="edit_expired")
            consumed_val = st.selectbox("Consumed?", ['No', 'Yes'], index=row['consumed'], key="edit_consumed")
            if st.button("Update Status", key="update_status_btn"):
                execute("UPDATE solution_id_tbl SET expired=%s, consumed=%s WHERE solution_id=%s",
                        (int(expired_val == "Yes"), int(consumed_val == "Yes"), edit_id))
                st.success("Status updated!")
                st.experimental_rerun()
        st.dataframe(solution_df)
    else:
        st.info("No Solution IDs yet.")

with st.form("solution_id_form", clear_on_submit=True):
    next_id = get_next_id("solution_id_tbl", "SOL", "solution_id")
    st.markdown(f"**Auto-generated Solution ID:** `{next_id}` _(will only be saved on submit)_")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['No', 'Yes'], index=0)
    consumed = st.selectbox("Consumed?", ['No', 'Yes'], index=0)
    sol_date = st.date_input("Solution ID Creation Date", value=datetime.today())
    submit_solution = st.form_submit_button("Submit New Solution ID")
    if submit_solution:
        execute(
            "INSERT INTO solution_id_tbl (solution_id, type, expired, consumed, date) VALUES (%s, %s, %s, %s, %s)",
            (next_id, solution_type, int(expired=="Yes"), int(consumed=="Yes"), sol_date)
        )
        st.success(":white_check_mark: Solution ID saved!")
        st.experimental_rerun()

solution_df = fetch_df("SELECT * FROM solution_id_tbl")

# ========== 2. PREP DATA TABLE =============
st.header("🔹 Solution Prep Data Entry")
prep_valid_df = solution_df[(solution_df['type'] == "New") & ~((solution_df['expired'] == 1) & (solution_df['consumed'] == 1))]
prep_valid_ids = prep_valid_df['solution_id'].tolist()

selected_solution_fk = st.selectbox("Select Solution ID", options=prep_valid_ids, key="prep_solution_fk")
existing_record = prep_df.loc[prep_df['solution_id_fk'] == selected_solution_fk].iloc[0] if (not prep_df.empty and selected_solution_fk in prep_df['solution_id_fk'].values) else None

with st.form("prep_data_form"):
    prep_existing_ids = prep_df['solution_prep_id'].tolist() if not prep_df.empty else []
    prep_id = safe_get(existing_record, 'solution_prep_id', get_next_id("solution_prep_data_tbl", "PREP", "solution_prep_id"))
    st.markdown(f"**Prep ID:** `{prep_id}`")
    desired_conc = st.number_input("Desired Solution Concentration (%)", value=float(safe_get(existing_record, 'desired_solution_concentration', 0.0)), format="%.2f")
    final_volume = st.number_input("Desired Final Volume (ml)", value=float(safe_get(existing_record, 'desired_final_volume', 0.0)), format="%.2f")
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'], index=['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(safe_get(existing_record, "solvent", "IPA")) if existing_record is not None else 0)
    solvent_lot = st.text_input("Solvent Lot Number", value=safe_get(existing_record, "solvent_lot_number", ""))
    solvent_weight = st.number_input("Solvent Weight Measured (g)", value=float(safe_get(existing_record, "solvent_weight_measured_g", 0.0)), format="%.3f")
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'], index=['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(safe_get(existing_record, "polymer", "CMS-72")) if existing_record is not None else 0)
    polymer_conc = st.number_input("Polymer starting concentration (%)", value=float(safe_get(existing_record, "polymer_starting_concentration", 0.0)), format="%.3f")
    polymer_lot = st.text_input("Polymer Lot Number", value=safe_get(existing_record, "polymer_lot_number", ""))
    polymer_weight = st.number_input("Polymer Weight Measured (g)", value=float(safe_get(existing_record, "polymer_weight_measured_g", 0.0)), format="%.3f")
    try:
        prep_date = pd.to_datetime(safe_get(existing_record, "prep_date", str(datetime.today().date()))).date()
    except:
        prep_date = datetime.today().date()
    prep_date = st.date_input("Prep Date", value=prep_date, key="prep_date_input")
    initials = st.text_input("Initials", value=safe_get(existing_record, "initials", ""))
    notes = st.text_area("Notes", value=safe_get(existing_record, "notes", ""))
    c_sol_conc_value = polymer_weight / (solvent_weight + polymer_weight) if (solvent_weight + polymer_weight) > 0 else 0.0
    st.markdown(
        f"""<div style="padding:8px 0 8px 0">
        <b>C-Solution Concentration <span style="font-weight:normal;">(polymer/(solvent+polymer)):</span></b>
        <code style="background:#E9F7EF; color:#247146; font-size:18px;">{c_sol_conc_value:.4f}</code>
        </div>""",
        unsafe_allow_html=True,
    )
    c_label_jar = st.text_input("C-Label for jar", value=safe_get(existing_record, "c_label_for_jar", ""))
    this_row_date = st.date_input("Date (Record Creation/Update)", value=datetime.today().date(), key="prep_row_date")
    submit_prep = st.form_submit_button("Submit/Update Prep Details")
    if submit_prep:
        # if updating, remove old record (optional: could use UPDATE here for smarter logic)
        if existing_record is not None:
            execute("DELETE FROM solution_prep_data_tbl WHERE solution_prep_id=%s", (prep_id,))
        execute(
            """INSERT INTO solution_prep_data_tbl (
                solution_prep_id, solution_id_fk, desired_solution_concentration, desired_final_volume,
                solvent, solvent_lot_number, solvent_weight_measured_g, polymer,
                polymer_starting_concentration, polymer_lot_number, polymer_weight_measured_g, prep_date,
                initials, notes, c_solution_concentration, c_label_for_jar, date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (prep_id, selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot, solvent_weight,
             polymer, polymer_conc, polymer_lot, polymer_weight, prep_date, initials, notes, c_sol_conc_value, c_label_jar, this_row_date)
        )
        # Update Solution ID Tbl's C-Solution Conc as well
        execute("UPDATE solution_id_tbl SET c_solution_conc=%s WHERE solution_id=%s", (c_sol_conc_value, selected_solution_fk))
        st.success(":white_check_mark: Prep Data submitted/updated!")
        st.experimental_rerun()

prep_df = fetch_df("SELECT * FROM solution_prep_data_tbl")

# ========== 3. COMBINED SOLUTION ENTRY =============
st.header("🔹 Combined Solution Entry")
combined_id = get_next_id("combined_solution_tbl", "COMB", "combined_id")
combined_type_ids = solution_df[solution_df['type']=="Combined"]['solution_id'].tolist()

solution_options = []
sid_to_conc = {}
for sid in combined_type_ids:
    c = float(solution_df.loc[solution_df['solution_id']==sid, 'c_solution_conc'].fillna(0).iloc[0])
    label = f"{sid} | Conc: {c:.4f}"
    solution_options.append(label)
    sid_to_conc[sid] = c

with st.form("combined_solution_form", clear_on_submit=True):
    solution_id_a_label = st.selectbox("Solution ID A", options=solution_options, key="comb_a")
    solution_id_b_label = st.selectbox("Solution ID B", options=[x for x in solution_options if x != solution_id_a_label], key="comb_b")
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    sid_a = solution_id_a_label.split(" |")[0]
    sid_b = solution_id_b_label.split(" |")[0]
    conc_a = sid_to_conc.get(sid_a, 0)
    conc_b = sid_to_conc.get(sid_b, 0)
    combined_mass = solution_mass_a + solution_mass_b
    combined_conc = ((solution_mass_a * conc_a) + (solution_mass_b * conc_b)) / combined_mass if combined_mass > 0 else 0.0
    st.markdown(f"**Combined Solution Concentration (calculated):** `{combined_conc:.4f}`")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Initials")
    combined_notes = st.text_area("Notes")
    this_row_date = st.date_input("Date (Record Creation/Update)", value=datetime.today().date(), key="combined_row_date")
    submit_combined = st.form_submit_button("Submit Combined Solution Details")
    if submit_combined:
        execute(
            """INSERT INTO combined_solution_tbl (
                combined_id, solution_id_a, solution_id_b, solution_mass_a_g, solution_mass_b_g,
                combined_solution_concentration, combined_date, initials, notes, date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (combined_id, sid_a, sid_b, solution_mass_a, solution_mass_b, combined_conc,
             combined_date, combined_initials, combined_notes, this_row_date)
        )
        st.success(":white_check_mark: Combined Solution saved!")
        st.experimental_rerun()

# ========== 4. DATA PREVIEWS & DATE FILTER ===========
st.header("📅 Solution Management Data Preview")

def filter_table(df, date_col='date', default_days=7):
    if df.empty or date_col not in df.columns:
        return df
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    today = datetime.today().date()
    min_date = df[date_col].dropna().min().date() if df[date_col].notnull().any() else today - timedelta(days=default_days)
    max_date = df[date_col].dropna().max().date() if df[date_col].notnull().any() else today
    filter_start, filter_end = st.date_input(f"Date range for {date_col}:", (min_date, max_date), key=f"filter_{date_col}")
    mask = (df[date_col].dt.date >= filter_start) & (df[date_col].dt.date <= filter_end)
    return df.loc[mask]

st.subheader("Solution ID Table")
st.dataframe(filter_table(fetch_df("SELECT * FROM solution_id_tbl"), date_col='date'))

st.subheader("Solution Prep Data Table")
st.dataframe(filter_table(fetch_df("SELECT * FROM solution_prep_data_tbl"), date_col='date'))

st.subheader("Combined Solution Data Table")
st.dataframe(filter_table(fetch_df("SELECT * FROM combined_solution_tbl"), date_col='date'))
