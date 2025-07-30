import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta

# --- DB Config ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Ardenttechnologies@1',
    'database': 'rnd_new_database'
}

def get_conn():
    return mysql.connector.connect(**db_config)

def fetch_df(query, params=None):
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_sql(query, params=None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    cursor.close()
    conn.close()

# --- Helper: Get Next Auto-increment ID ---
def get_next_id(table, id_col, prefix):
    df = fetch_df(f"SELECT {id_col} FROM {table}")
    nums = []
    for sid in df[id_col]:
        if isinstance(sid, str) and sid.startswith(prefix):
            try:
                nums.append(int(sid.replace(prefix + "-", "")))
            except: continue
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{str(next_num).zfill(3)}"

st.title("📄 Solution Management Form (MySQL Backend)")

# ========== 1. Solution ID Table ==========

st.header("🔹 Solution ID Entry / Management")

df_solution = fetch_df("SELECT * FROM solution_id_tbl")
df_solution['Label'] = df_solution.apply(lambda row:
    f"{row['solution_id']} (expired)" if row['expired'] else
    f"{row['solution_id']} (consumed)" if row['consumed'] else
    f"{row['solution_id']} (combined)" if row['type'] == "Combined" else
    row['solution_id'], axis=1
)
st.dataframe(df_solution)

# Insert New Solution ID
with st.form("solution_id_form", clear_on_submit=True):
    next_id = get_next_id("solution_id_tbl", "solution_id", "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{next_id}`")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['No', 'Yes']) == "Yes"
    consumed = st.selectbox("Consumed?", ['No', 'Yes']) == "Yes"
    sol_date = st.date_input("Creation Date", value=datetime.today())
    submit_solution = st.form_submit_button("Submit New Solution ID")
    if submit_solution:
        execute_sql(
            "INSERT INTO solution_id_tbl (solution_id, type, expired, consumed, date) VALUES (%s, %s, %s, %s, %s)",
            (next_id, solution_type, int(expired), int(consumed), sol_date.strftime("%Y-%m-%d"))
        )
        st.success("Solution ID saved!")
        st.experimental_rerun()

# ========== 2. Solution Prep Data ==========

st.header("🔹 Solution Prep Data Entry")

df_prep = fetch_df("SELECT * FROM solution_prep_data_tbl")
valid_ids = df_solution[(df_solution['type'] == 'New') & ~(df_solution['expired'] & df_solution['consumed'])]['solution_id'].tolist()
selected_solution_fk = st.selectbox("Select Solution ID", options=valid_ids)
existing_prep = df_prep[df_prep['solution_id_fk'] == selected_solution_fk].to_dict('records')
existing_record = existing_prep[0] if existing_prep else None

with st.form("prep_data_form"):
    prep_id = get_next_id("solution_prep_data_tbl", "solution_prep_id", "PREP")
    st.markdown(f"**Prep ID:** `{prep_id}`")
    desired_conc = st.number_input("Desired Solution Concentration (%)", value=0.0, format="%.2f")
    final_volume = st.number_input("Desired Final Volume (ml)", value=0.0, format="%.1f")
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'])
    solvent_lot = st.text_input("Solvent Lot Number")
    solvent_weight = st.number_input("Solvent Weight Measured (g)", value=0.0, format="%.2f")
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'])
    polymer_conc = st.number_input("Polymer starting concentration (%)", value=0.0, format="%.2f")
    polymer_lot = st.text_input("Polymer Lot Number")
    polymer_weight = st.number_input("Polymer Weight Measured (g)", value=0.0, format="%.2f")
    prep_date = st.date_input("Prep Date", value=datetime.today())
    initials = st.text_input("Initials")
    notes = st.text_area("Notes")
    c_sol_conc_value = polymer_weight / (solvent_weight + polymer_weight) if (solvent_weight + polymer_weight) > 0 else 0.0
    st.markdown(f"C-Solution Concentration: **{c_sol_conc_value:.4f}**")
    c_label_jar = st.text_input("C-Label for jar")
    this_row_date = st.date_input("Date (Record Creation/Update)", value=datetime.today())
    submit_prep = st.form_submit_button("Submit/Update Prep Details")
    if submit_prep:
        execute_sql("""
            INSERT INTO solution_prep_data_tbl
                (solution_prep_id, solution_id_fk, desired_solution_concentration, desired_final_volume,
                solvent, solvent_lot_number, solvent_weight_measured_g, polymer,
                polymer_starting_concentration, polymer_lot_number, polymer_weight_measured_g, prep_date,
                initials, notes, c_solution_concentration, c_label_for_jar, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            prep_id, selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot,
            solvent_weight, polymer, polymer_conc, polymer_lot, polymer_weight, prep_date.strftime("%Y-%m-%d"),
            initials, notes, c_sol_conc_value, c_label_jar, this_row_date.strftime("%Y-%m-%d")
        ))
        st.success("Prep Data submitted!")
        st.experimental_rerun()

# ========== 3. Combined Solution Entry ==========

st.header("🔹 Combined Solution Entry")
df_combined = fetch_df("SELECT * FROM combined_solution_tbl")
combined_id = get_next_id("combined_solution_tbl", "combined_id", "COMB")
combined_ids = df_solution[df_solution['type'] == 'Combined']['solution_id'].tolist()
solution_options = combined_ids

solution_id_a = st.selectbox("Solution ID A", options=solution_options)
solution_id_b = st.selectbox("Solution ID B", options=[x for x in solution_options if x != solution_id_a])
solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
# Fetch latest C-Solution Concentration for both IDs
def get_c_conc(sid):
    sub = df_prep[df_prep['solution_id_fk'] == sid]
    if not sub.empty:
        return float(sub.iloc[-1]['c_solution_concentration'])
    return 0.0

conc_a = get_c_conc(solution_id_a)
conc_b = get_c_conc(solution_id_b)
combined_mass = solution_mass_a + solution_mass_b
combined_conc = ((solution_mass_a * conc_a) + (solution_mass_b * conc_b)) / combined_mass if combined_mass > 0 else 0.0

combined_date = st.date_input("Combined Date")
combined_initials = st.text_input("Initials (Combined)")
combined_notes = st.text_area("Notes (Combined)")
this_row_date = st.date_input("Date (Combined Record Creation/Update)", value=datetime.today())
if st.button("Submit Combined Solution Details"):
    execute_sql("""
        INSERT INTO combined_solution_tbl
            (combined_id, solution_id_a, solution_id_b, solution_mass_a_g, solution_mass_b_g,
            combined_solution_concentration, combined_date, initials, notes, date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        combined_id, solution_id_a, solution_id_b, solution_mass_a, solution_mass_b,
        combined_conc, combined_date.strftime("%Y-%m-%d"), combined_initials, combined_notes, this_row_date.strftime("%Y-%m-%d")
    ))
    st.success("Combined Solution saved!")
    st.experimental_rerun()

# ========== Data Preview ==========

st.subheader("📅 Solution Management Data Preview")
st.write("### Solution ID Table")
st.dataframe(df_solution)
st.write("### Solution Prep Data Table")
st.dataframe(df_prep)
st.write("### Combined Solution Data Table")
st.dataframe(df_combined)
