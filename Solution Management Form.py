import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta

# ---------- MySQL Config ----------
db_config = {
    'user': 'root',
    'password': 'Ardenttechnologies@1',
    'host': 'localhost',
    'database': 'rnd_new_database'
}

def get_conn():
    return mysql.connector.connect(**db_config)

def fetchall_df(query, params=None):
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_query(query, params=None, commit=True):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(query, params)
    if commit:
        conn.commit()
    cursor.close()
    conn.close()

def get_last_id_from_records(records, id_prefix):
    ids = set()
    for val in records:
        vstr = str(val).strip()
        if vstr.startswith(id_prefix):
            ids.add(vstr)
    nums = []
    for rid in ids:
        try:
            suffix = rid.split('-')[-1]
            if suffix.isdigit():
                nums.append(int(suffix))
        except Exception:
            continue
    next_num = max(nums) + 1 if nums else 1
    return f"{id_prefix}-{str(next_num).zfill(3)}"

def safe_get(record, key, default=""):
    if isinstance(record, dict):
        for k, v in record.items():
            if k.strip().lower() == key.strip().lower():
                return v
    elif isinstance(record, pd.Series):
        return record.get(key, default)
    return default

def parse_date(date_val):
    if isinstance(date_val, datetime):
        return date_val
    elif isinstance(date_val, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_val.strip(), fmt)
            except:
                continue
    return None

def label_status(row):
    label = row["solution_id"]
    if row.get("expired", "No") == "Yes":
        label += " (expired)"
    elif row.get("consumed", "No") == "Yes":
        label += " (consumed)"
    elif row.get("type", "New") == "Combined":
        label += " (combined)"
    return label

def display_table_with_date_filter(df, headers, table_title, date_col="date", default_days=7):
    st.markdown(f"### {table_title}")
    if df.empty:
        st.write("No records.")
        return
    for col in headers:
        if col not in df.columns:
            df[col] = ""
    df = df[headers]
    if date_col in df.columns:
        df[date_col] = df[date_col].astype(str).replace("nan", "")
    valid_dates = []
    for d in df[date_col]:
        parsed = parse_date(d)
        if parsed:
            valid_dates.append(parsed)
    if valid_dates:
        min_date = min(valid_dates).date()
        max_date = max(valid_dates).date()
    else:
        today = datetime.today().date()
        min_date, max_date = today - timedelta(days=default_days), today
    filter_start, filter_end = st.date_input(f"Select {table_title} date range", (min_date, max_date), key=f"{table_title}_date_range")
    bool_index = []
    for d in df[date_col]:
        parsed = parse_date(d)
        if parsed and filter_start <= parsed.date() <= filter_end:
            bool_index.append(True)
        else:
            bool_index.append(False)
    filtered = df[bool_index]
    if not filtered.empty:
        st.dataframe(filtered)
    else:
        st.write(f"No records found for selected date range.")

# ---------- Table headers ----------
SOLUTION_ID_HEADERS = ["solution_id", "type", "expired", "consumed", "date"]
PREP_HEADERS = [
    "solution_prep_id", "solution_id_fk", "desired_solution_concentration", "desired_final_volume",
    "solvent", "solvent_lot_number", "solvent_weight_measured_g", "polymer",
    "polymer_starting_concentration", "polymer_lot_number", "polymer_weight_measured_g",
    "prep_date", "initials", "notes", "c_solution_concentration", "c_label_for_jar", "date"
]
COMBINED_HEADERS = [
    "combined_id", "solution_id_a", "solution_id_b", "solution_mass_a_g", "solution_mass_b_g",
    "combined_solution_concentration", "combined_date", "initials", "notes", "date"
]

# ---------- DATA LOAD ----------
df_solution = fetchall_df("SELECT * FROM solution_id_tbl")
df_prep_data = fetchall_df("SELECT * FROM solution_prep_data_tbl")
df_combined = fetchall_df("SELECT * FROM combined_solution_tbl")

st.markdown("# 📄 Solution Management Form")
st.markdown("Manage creation, preparation, and combination of solutions.")

# ====================== Solution ID Management ======================
st.markdown("## 🔹 Solution ID Entry / Management")
with st.expander("View / Update Existing Solution IDs", expanded=False):
    if not df_solution.empty:
        df_solution["Label"] = df_solution.apply(label_status, axis=1)
        st.dataframe(df_solution[["solution_id", "type", "expired", "consumed", "date"]])
        to_edit = st.selectbox("Select Solution ID to update", options=[""] + df_solution["solution_id"].tolist())
        if to_edit:
            idx = df_solution[df_solution["solution_id"] == to_edit].index[0]
            expired_val = st.selectbox("Expired?", ["No", "Yes"], index=0 if df_solution.at[idx,"expired"]=="No" else 1, key="edit_expired")
            consumed_val = st.selectbox("Consumed?", ["No", "Yes"], index=0 if df_solution.at[idx,"consumed"]=="No" else 1, key="edit_consumed")
            if st.button("Update Status", key="update_status_btn"):
                update_sql = "UPDATE solution_id_tbl SET expired=%s, consumed=%s WHERE solution_id=%s"
                execute_query(update_sql, (expired_val, consumed_val, to_edit))
                st.success("Status updated!")
                st.experimental_rerun()
    else:
        st.info("No Solution IDs yet.")

with st.form("solution_id_form", clear_on_submit=True):
    next_id = get_last_id_from_records(df_solution["solution_id"].tolist(), "SOL")
    st.markdown(f"**Auto-generated Solution ID:** `{next_id}` _(will only be saved on submit)_")
    solution_type = st.selectbox("Type", ['New', 'Combined'])
    expired = st.selectbox("Expired?", ['No', 'Yes'], index=0)
    consumed = st.selectbox("Consumed?", ['No', 'Yes'], index=0)
    sol_date = st.date_input("Solution ID Creation Date", value=datetime.today())
    submit_solution = st.form_submit_button("Submit New Solution ID")
    if submit_solution:
        insert_sql = "INSERT INTO solution_id_tbl (solution_id, type, expired, consumed, date) VALUES (%s, %s, %s, %s, %s)"
        execute_query(insert_sql, (next_id, solution_type, expired, consumed, sol_date.strftime("%Y-%m-%d")))
        st.success(":white_check_mark: Solution ID saved!")
        st.experimental_rerun()

# Reload after insert/update
df_solution = fetchall_df("SELECT * FROM solution_id_tbl")

# ====================== Solution Prep Data Entry ======================
st.markdown("---")
st.markdown("## 🔹 Solution Prep Data Entry")
prep_valid_df = df_solution[
    (df_solution['type'] == "New") & 
    ~((df_solution['expired'] == "Yes") & (df_solution['consumed'] == "Yes"))
]
prep_valid_ids = prep_valid_df["solution_id"].tolist()

selected_solution_fk = st.selectbox("Select Solution ID", options=prep_valid_ids, key="prep_solution_fk")
prep_entries = df_prep_data[df_prep_data["solution_id_fk"] == selected_solution_fk]
existing_record = prep_entries.iloc[0] if not prep_entries.empty else None
if existing_record is not None:
    st.info("⚠️ Existing prep entry found. Fields prefilled for update.")
else:
    st.success("✅ No prep entry found. Enter new details.")

with st.form("prep_data_form"):
    all_prep_ids = df_prep_data["solution_prep_id"].tolist()
    prep_id = safe_get(existing_record, "solution_prep_id", get_last_id_from_records(all_prep_ids, "PREP"))
    st.markdown(f"**Prep ID:** `{prep_id}`")
    desired_conc = st.number_input(
        "Desired Solution Concentration (%)",
        value=float(safe_get(existing_record, "desired_solution_concentration", 0.0)),
        format="%.2f"
    )
    final_volume = st.number_input(
        "Desired Final Volume (ml)",
        value=float(safe_get(existing_record, "desired_final_volume", 0.0)),
        format="%.1f"
    )
    solvent = st.selectbox("Solvent", ['IPA', 'EtOH', 'Heptane', 'Novec 7300'],
        index=['IPA', 'EtOH', 'Heptane', 'Novec 7300'].index(safe_get(existing_record, "solvent", "IPA")) if existing_record is not None else 0
    )
    solvent_lot = st.text_input("Solvent Lot Number", value=safe_get(existing_record, "solvent_lot_number", ""))
    solvent_weight = st.number_input("Solvent Weight Measured (g)",
        value=float(safe_get(existing_record, "solvent_weight_measured_g", 0.0)), format="%.2f"
    )
    polymer = st.selectbox("Polymer", ['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'],
        index=['CMS-72', 'CMS-335', 'CMS-34', 'CMS-7'].index(safe_get(existing_record, "polymer", "CMS-72")) if existing_record is not None else 0
    )
    polymer_conc = st.number_input("Polymer starting concentration (%)",
        value=float(safe_get(existing_record, "polymer_starting_concentration", 0.0)), format="%.2f"
    )
    polymer_lot = st.text_input("Polymer Lot Number", value=safe_get(existing_record, "polymer_lot_number", ""))
    polymer_weight = st.number_input("Polymer Weight Measured (g)",
        value=float(safe_get(existing_record, "polymer_weight_measured_g", 0.0)), format="%.2f"
    )
    prep_date_str = safe_get(existing_record, "prep_date")
    try:
        prep_date = datetime.strptime(prep_date_str, "%Y-%m-%d").date() if prep_date_str else datetime.today().date()
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
        if existing_record is not None:
            update_sql = """
                UPDATE solution_prep_data_tbl SET
                    solution_id_fk=%s, desired_solution_concentration=%s, desired_final_volume=%s,
                    solvent=%s, solvent_lot_number=%s, solvent_weight_measured_g=%s, polymer=%s,
                    polymer_starting_concentration=%s, polymer_lot_number=%s, polymer_weight_measured_g=%s,
                    prep_date=%s, initials=%s, notes=%s, c_solution_concentration=%s, c_label_for_jar=%s, date=%s
                WHERE solution_prep_id=%s
            """
            execute_query(update_sql, (
                selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot, solvent_weight,
                polymer, polymer_conc, polymer_lot, polymer_weight, prep_date.strftime("%Y-%m-%d"),
                initials, notes, c_sol_conc_value, c_label_jar, this_row_date.strftime("%Y-%m-%d"), prep_id
            ))
            st.success(":white_check_mark: Prep Data updated!")
        else:
            insert_sql = """
                INSERT INTO solution_prep_data_tbl (
                    solution_prep_id, solution_id_fk, desired_solution_concentration, desired_final_volume,
                    solvent, solvent_lot_number, solvent_weight_measured_g, polymer,
                    polymer_starting_concentration, polymer_lot_number, polymer_weight_measured_g, prep_date,
                    initials, notes, c_solution_concentration, c_label_for_jar, date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_query(insert_sql, (
                prep_id, selected_solution_fk, desired_conc, final_volume, solvent, solvent_lot, solvent_weight,
                polymer, polymer_conc, polymer_lot, polymer_weight, prep_date.strftime("%Y-%m-%d"),
                initials, notes, c_sol_conc_value, c_label_jar, this_row_date.strftime("%Y-%m-%d")
            ))
            st.success(":white_check_mark: Prep Data submitted!")
        st.experimental_rerun()

df_solution = fetchall_df("SELECT * FROM solution_id_tbl")
df_prep_data = fetchall_df("SELECT * FROM solution_prep_data_tbl")

# ====================== Combined Solution Entry ======================
st.markdown("---")
st.markdown("## 🔹 Combined Solution Entry")

combined_id = get_last_id_from_records(df_combined["combined_id"].tolist(), "COMB")
valid_comb_df = df_solution[
    (df_solution["type"] == "Combined") &
    ((df_solution['consumed'] == "No") | (df_solution['expired'] == "No"))
]
valid_comb_ids = valid_comb_df["solution_id"].unique().tolist()

solution_options = []
sid_to_conc = {}
for sid in valid_comb_ids:
    preps = df_prep_data[df_prep_data["solution_id_fk"] == sid]
    c = 0.0
    if not preps.empty:
        preps = preps.sort_values("prep_date", ascending=False)
        latest_prep = preps.iloc[0]
        c = float(latest_prep.get("c_solution_concentration", 0) or 0)
    label = f"{sid} | Conc: {c:.4f}"
    solution_options.append(label)
    sid_to_conc[sid] = c

st.markdown(f"**Auto-generated Combined ID:** `{combined_id}`")
with st.form("combined_solution_form", clear_on_submit=True):
    st.markdown("**Select Solution IDs to Combine:**")
    solution_id_a = st.selectbox("Solution ID A", options=solution_options, key="comb_a")
    solution_id_b = st.selectbox(
        "Solution ID B",
        options=[x for x in solution_options if x != solution_id_a],
        key="comb_b"
    )
    solution_mass_a = st.number_input("Solution Mass A (g)", format="%.2f")
    solution_mass_b = st.number_input("Solution Mass B (g)", format="%.2f")
    sid_a = solution_id_a.split(" |")[0]
    sid_b = solution_id_b.split(" |")[0]
    conc_a = sid_to_conc.get(sid_a, 0)
    conc_b = sid_to_conc.get(sid_b, 0)
    combined_mass = solution_mass_a + solution_mass_b
    combined_conc = ((solution_mass_a * conc_a) + (solution_mass_b * conc_b)) / combined_mass if combined_mass > 0 else 0.0
    st.markdown(f"**Combined Solution Concentration (calculated):** `{combined_conc:.4f}`")
    st.warning("Check with your team: Do you ever combine different concentrations? This form will auto-calculate if you do.")
    combined_date = st.date_input("Combined Date")
    combined_initials = st.text_input("Initials")
    combined_notes = st.text_area("Notes")
    this_row_date = st.date_input("Date (Record Creation/Update)", value=datetime.today().date(), key="combined_row_date")
    submit_combined = st.form_submit_button("Submit Combined Solution Details")
    if submit_combined:
        insert_sql = """
            INSERT INTO combined_solution_tbl (
                combined_id, solution_id_a, solution_id_b, solution_mass_a_g, solution_mass_b_g,
                combined_solution_concentration, combined_date, initials, notes, date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(insert_sql, (
            combined_id, sid_a, sid_b, solution_mass_a, solution_mass_b, combined_conc,
            combined_date.strftime("%Y-%m-%d"), combined_initials, combined_notes, this_row_date.strftime("%Y-%m-%d")
        ))
        st.success(":white_check_mark: Combined Solution saved!")
        st.experimental_rerun()

df_combined = fetchall_df("SELECT * FROM combined_solution_tbl")

# ================= PREVIEW TABLES WITH DATE FILTERS =================

st.markdown("## 📅 Solution Management Data Preview")

display_table_with_date_filter(
    df_solution,
    SOLUTION_ID_HEADERS,
    "Solution ID Table"
)

display_table_with_date_filter(
    df_prep_data,
    PREP_HEADERS,
    "Solution Prep Data Table"
)

display_table_with_date_filter(
    df_combined,
    COMBINED_HEADERS,
    "Combined Solution Data Table"
)
