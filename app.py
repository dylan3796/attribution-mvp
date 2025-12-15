import sqlite3
import uuid
import pandas as pd
import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Attribution MVP", layout="wide")

DB_PATH = "attribution.db"
DEFAULT_SETTINGS = {
    "enforce_split_cap": "true",  # whether account-level splits must sum to <= 100%
}

# ----------------------------
# DB helpers
# ----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def run_sql(sql: str, params: tuple = ()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()

def read_sql(sql: str, params: tuple = ()):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def init_db():
    run_sql("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_id TEXT PRIMARY KEY,
        account_name TEXT NOT NULL
    );
    """)
    run_sql("""
    CREATE TABLE IF NOT EXISTS partners (
        partner_id TEXT PRIMARY KEY,
        partner_name TEXT NOT NULL
    );
    """)
    run_sql("""
    CREATE TABLE IF NOT EXISTS use_cases (
        use_case_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        use_case_name TEXT NOT NULL,
        stage TEXT,
        estimated_value REAL,
        target_close_date TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
    );
    """)
    run_sql("""
    CREATE TABLE IF NOT EXISTS use_case_partners (
        use_case_id TEXT NOT NULL,
        partner_id TEXT NOT NULL,
        partner_role TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (use_case_id, partner_id),
        FOREIGN KEY (use_case_id) REFERENCES use_cases(use_case_id),
        FOREIGN KEY (partner_id) REFERENCES partners(partner_id)
    );
    """)
    run_sql("""
    CREATE TABLE IF NOT EXISTS account_partners (
        account_id TEXT NOT NULL,
        partner_id TEXT NOT NULL,
        split_percent REAL NOT NULL,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'auto',
        PRIMARY KEY (account_id, partner_id),
        FOREIGN KEY (account_id) REFERENCES accounts(account_id),
        FOREIGN KEY (partner_id) REFERENCES partners(partner_id)
    );
    """)
    run_sql("""
    CREATE TABLE IF NOT EXISTS revenue_events (
        revenue_date TEXT NOT NULL,
        account_id TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
    );
    """)
    run_sql("""
    CREATE TABLE IF NOT EXISTS settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL
    );
    """)

    # lightweight migrations for existing DB files
    def ensure_column(table: str, column: str, definition: str):
        cols = read_sql(f"PRAGMA table_info({table});")["name"].tolist()
        if column not in cols:
            run_sql(f"ALTER TABLE {table} ADD COLUMN {definition};")

    ensure_column("use_cases", "stage", "stage TEXT")
    ensure_column("use_cases", "estimated_value", "estimated_value REAL")
    ensure_column("use_cases", "target_close_date", "target_close_date TEXT")
    ensure_column("account_partners", "source", "source TEXT NOT NULL DEFAULT 'auto'")

    # ensure settings table has defaults
    existing_settings = read_sql("SELECT setting_key FROM settings;")
    for key, val in DEFAULT_SETTINGS.items():
        if key not in existing_settings["setting_key"].tolist():
            run_sql("INSERT INTO settings(setting_key, setting_value) VALUES (?, ?);", (key, val))

def seed_data_if_empty():
    existing = read_sql("SELECT COUNT(*) as c FROM accounts;")
    if int(existing.loc[0, "c"]) > 0:
        return

    accounts = [
        ("A1", "Acme Corp"),
        ("A2", "Bluebird Health"),
        ("A3", "Canyon Bank"),
        ("A4", "Dune Retail"),
        ("A5", "Evergreen Manufacturing"),
    ]
    for a in accounts:
        run_sql("INSERT INTO accounts(account_id, account_name) VALUES (?, ?);", a)

    partners = [
        ("P1", "Titan SI"),
        ("P2", "Northwind Consulting"),
        ("P3", "Orbit ISV"),
    ]
    for p in partners:
        run_sql("INSERT INTO partners(partner_id, partner_name) VALUES (?, ?);", p)

    use_cases = [
        ("UC1", "A1", "Lakehouse Migration", "Discovery", 750000, (date.today() + timedelta(days=45)).isoformat()),
        ("UC2", "A1", "GenAI Support Bot", "Evaluation", 400000, (date.today() + timedelta(days=25)).isoformat()),
        ("UC3", "A2", "Claims Modernization", "Commit", 550000, (date.today() + timedelta(days=15)).isoformat()),
        ("UC4", "A3", "Fraud Detection", "Live", 300000, (date.today() - timedelta(days=10)).isoformat()),
        ("UC5", "A4", "Real-time Personalization", "Evaluation", 420000, (date.today() + timedelta(days=30)).isoformat()),
        ("UC6", "A5", "Manufacturing QA Analytics", "Discovery", 600000, (date.today() + timedelta(days=60)).isoformat()),
    ]
    for uc in use_cases:
        run_sql("""
        INSERT INTO use_cases(use_case_id, account_id, use_case_name, stage, estimated_value, target_close_date)
        VALUES (?, ?, ?, ?, ?, ?);
        """, uc)

    # Revenue events: last 60 days
    start = date.today() - timedelta(days=60)
    daily = [("A1", 500), ("A2", 250), ("A3", 180), ("A4", 220), ("A5", 300)]
    for i in range(61):
        d = start + timedelta(days=i)
        for account_id, base in daily:
            run_sql(
                "INSERT INTO revenue_events(revenue_date, account_id, amount) VALUES (?, ?, ?);",
                (d.isoformat(), account_id, float(base))
            )

def get_setting_bool(key: str, default: bool) -> bool:
    row = read_sql("SELECT setting_value FROM settings WHERE setting_key = ?;", (key,))
    if row.empty:
        return default
    val = str(row.loc[0, "setting_value"]).lower()
    return val in ["true", "1", "yes", "on"]

def set_setting_bool(key: str, value: bool):
    run_sql("""
    INSERT INTO settings(setting_key, setting_value)
    VALUES (?, ?)
    ON CONFLICT(setting_key)
    DO UPDATE SET setting_value = excluded.setting_value;
    """, (key, "true" if value else "false"))

def should_enforce_split_cap() -> bool:
    return get_setting_bool("enforce_split_cap", default=True)

def will_exceed_split_cap(account_id: str, partner_id: str, new_split: float) -> tuple[bool, float]:
    """
    Returns (exceeds, total_with_new). Excludes current partner's existing split when replacing.
    """
    current = read_sql("""
        SELECT partner_id, split_percent
        FROM account_partners
        WHERE account_id = ?;
    """, (account_id,))
    total_other = current[current["partner_id"] != partner_id]["split_percent"].sum()
    total_with_new = total_other + float(new_split)
    exceeds = total_with_new > 1.00001  # small tolerance
    return exceeds, total_with_new

def upsert_account_partner_from_use_case_partner(use_case_id: str, partner_id: str, partner_role: str, split_percent: float):
    # find account_id from use case
    uc = read_sql("SELECT account_id FROM use_cases WHERE use_case_id = ?;", (use_case_id,))
    if uc.empty:
        raise ValueError("use_case_id not found")

    account_id = uc.loc[0, "account_id"]
    today = date.today().isoformat()

    # upsert use_case_partner
    run_sql("""
    INSERT INTO use_case_partners(use_case_id, partner_id, partner_role, created_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(use_case_id, partner_id)
    DO UPDATE SET partner_role = excluded.partner_role;
    """, (use_case_id, partner_id, partner_role, today))

    # upsert account_partner (relationship hub) but do not override manual entries
    existing = read_sql("""
        SELECT source FROM account_partners
        WHERE account_id = ? AND partner_id = ?;
    """, (account_id, partner_id))

    if not existing.empty and existing.loc[0, "source"] == "manual":
        return {"status": "skipped_manual", "account_id": account_id}

    if should_enforce_split_cap():
        exceeds, total_with_new = will_exceed_split_cap(account_id, partner_id, split_percent)
        if exceeds:
            return {
                "status": "blocked_split_cap",
                "account_id": account_id,
                "total_with_new": total_with_new,
            }

    run_sql("""
    INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source)
    VALUES (?, ?, ?, ?, ?, 'auto')
    ON CONFLICT(account_id, partner_id)
    DO UPDATE SET
        split_percent = excluded.split_percent,
        last_seen = excluded.last_seen,
        source = 'auto';
    """, (account_id, partner_id, split_percent, today, today))

    return {"status": "upserted", "account_id": account_id}


def upsert_manual_account_partner(account_id: str, partner_id: str, split_percent: float):
    if should_enforce_split_cap():
        exceeds, total_with_new = will_exceed_split_cap(account_id, partner_id, split_percent)
        if exceeds:
            return {
                "status": "blocked_split_cap",
                "account_id": account_id,
                "total_with_new": total_with_new,
            }

    today = date.today().isoformat()
    run_sql("""
    INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source)
    VALUES (?, ?, ?, ?, ?, 'manual')
    ON CONFLICT(account_id, partner_id)
    DO UPDATE SET
        split_percent = excluded.split_percent,
        last_seen = excluded.last_seen,
        source = 'manual',
        first_seen = account_partners.first_seen;
    """, (account_id, partner_id, split_percent, today, today))
    return {"status": "upserted", "account_id": account_id}


def create_use_case(account_id: str, use_case_name: str, stage: str, estimated_value: float, target_close_date: str):
    use_case_id = f"UC-{uuid.uuid4().hex[:8].upper()}"
    run_sql("""
    INSERT INTO use_cases(use_case_id, account_id, use_case_name, stage, estimated_value, target_close_date)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (use_case_id, account_id, use_case_name, stage, estimated_value, target_close_date))
    return use_case_id

def reset_demo():
    import os
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    seed_data_if_empty()

# ----------------------------
# App
# ----------------------------
init_db()
seed_data_if_empty()

st.title("Attribution MVP (Streamlit)")

top_left, top_right = st.columns([1, 3])
with top_left:
    if st.button("Reset demo data (start fresh)"):
        reset_demo()
        st.success("Reset complete. Refresh the page.")

with top_right:
    st.caption("Transactional unit = Use Case between Partner & Customer. Auto rollup to AccountPartner + manual overrides.")

with st.expander("Settings"):
    enforce_default = should_enforce_split_cap()
    with st.form("settings_form"):
        enforce_cap = st.checkbox(
            "Enforce account split cap (≤ 100% total per account)",
            value=enforce_default,
            help="When ON, adding or updating splits will be blocked if the account's total would exceed 100%. Turn OFF to allow totals > 100%.",
        )
        save_settings = st.form_submit_button("Save settings")
        if save_settings:
            set_setting_bool("enforce_split_cap", enforce_cap)
            st.success(f"Saved. Enforce split cap = {'ON' if enforce_cap else 'OFF'}.")

left, right = st.columns([1, 1])

with left:
    st.subheader("1) Use Cases (transactional unit, provided)")
    st.caption("Use cases are assumed to be sourced externally (e.g., CRM). This view is read-only; we only link partners for attribution.")
    accounts = read_sql("SELECT account_id, account_name FROM accounts ORDER BY account_name;")

    use_cases = read_sql("""
        SELECT u.use_case_id, u.use_case_name, u.stage, u.estimated_value, u.target_close_date, a.account_name, a.account_id
        FROM use_cases u
        JOIN accounts a ON a.account_id = u.account_id
        ORDER BY a.account_name, u.use_case_name;
    """)
    if use_cases.empty:
        st.info("No use cases available. Add them to the database to enable attribution.")
    else:
        st.dataframe(use_cases, use_container_width=True)

    st.subheader("2) Link Partner to Use Case (auto AccountPartner)")
    partners = read_sql("SELECT partner_id, partner_name FROM partners ORDER BY partner_name;")

    if use_cases.empty or partners.empty:
        st.info("Need at least one use case and partner to create a UseCasePartner.")
    else:
        uc_label_map = {
            f"{row['account_name']} — {row['use_case_name']} [{(row['stage'] or 'Stage n/a') if pd.notnull(row['stage']) else 'Stage n/a'}] (${(row['estimated_value'] or 0):,.0f})": row["use_case_id"]
            for _, row in use_cases.iterrows()
        }
        p_label_map = {
            f"{row['partner_name']} ({row['partner_id']})": row["partner_id"]
            for _, row in partners.iterrows()
        }

        uc_choice = st.selectbox("Use case", list(uc_label_map.keys()))
        p_choice = st.selectbox("Partner", list(p_label_map.keys()))
        role_choice = st.selectbox("Partner role", ["Implementation (SI)", "Influence", "Referral", "ISV"])
        split = st.slider("Split % for account-level credit", 0, 100, 10) / 100.0

        if st.button("Save use case ↔ partner (auto rollup)"):
            result = upsert_account_partner_from_use_case_partner(
                use_case_id=uc_label_map[uc_choice],
                partner_id=p_label_map[p_choice],
                partner_role=role_choice,
                split_percent=split
            )
            if result["status"] == "skipped_manual":
                st.warning("UseCasePartner saved, but AccountPartner already set to manual and was left untouched.")
            elif result["status"] == "blocked_split_cap":
                st.error(f"Blocked: total account split would be {result['total_with_new']*100:.0f}%, which exceeds the 100% cap. Toggle off enforcement in Settings if you want to allow this.")
            else:
                st.success("Saved. UseCasePartner created/updated AND AccountPartner auto-upserted.")

    links = read_sql("""
        SELECT
            a.account_name,
            u.use_case_name,
            u.stage,
            p.partner_name,
            ucp.partner_role,
            ucp.created_at
        FROM use_case_partners ucp
        JOIN use_cases u ON u.use_case_id = ucp.use_case_id
        JOIN accounts a ON a.account_id = u.account_id
        JOIN partners p ON p.partner_id = ucp.partner_id
        ORDER BY a.account_name, u.use_case_name, p.partner_name;
    """)
    if not links.empty:
        st.caption("Use Case ↔ Partner links (auto rollup sources)")
        st.dataframe(links, use_container_width=True)

with right:
    st.subheader("3) AccountPartner 360 (auto + manual)")

    ap = read_sql("""
      SELECT ap.account_id, a.account_name, ap.partner_id, p.partner_name, ap.split_percent, ap.first_seen, ap.last_seen, ap.source
      FROM account_partners ap
      JOIN accounts a ON a.account_id = ap.account_id
      JOIN partners p ON p.partner_id = ap.partner_id
      ORDER BY a.account_name, p.partner_name;
    """)

    if ap.empty:
        st.info("No AccountPartner relationships yet. Auto-create from a UseCasePartner or add manually below.")
    else:
        st.dataframe(ap, use_container_width=True)

    st.subheader("Manual AccountPartner (override or add)")
    if accounts.empty or partners.empty:
        st.info("Need accounts and partners to add a manual AccountPartner.")
    else:
        with st.form("manual_account_partner"):
            acct_map_manual = {f"{row['account_name']} ({row['account_id']})": row["account_id"] for _, row in accounts.iterrows()}
            partner_map_manual = {f"{row['partner_name']} ({row['partner_id']})": row["partner_id"] for _, row in partners.iterrows()}
            ap_account_choice = st.selectbox("Customer account", list(acct_map_manual.keys()))
            ap_partner_choice = st.selectbox("Partner", list(partner_map_manual.keys()))
            ap_split = st.slider("Split %", 0, 100, 20) / 100.0
            manual_submit = st.form_submit_button("Save manual AccountPartner (locks source=manual)")

            if manual_submit:
                result = upsert_manual_account_partner(
                    account_id=acct_map_manual[ap_account_choice],
                    partner_id=partner_map_manual[ap_partner_choice],
                    split_percent=ap_split,
                )
                if result["status"] == "blocked_split_cap":
                    st.error(f"Blocked: total account split would be {result['total_with_new']*100:.0f}%, which exceeds the 100% cap. Toggle off enforcement in Settings if you want to allow this.")
                else:
                    st.success("Manual AccountPartner saved (source=manual). Future auto rollups will not overwrite this row.")

    st.subheader("Partner Impact (rollup)")
    partner_impact = read_sql("""
      SELECT
        p.partner_name,
        COUNT(DISTINCT ap.account_id) AS accounts_influenced,
        ROUND(SUM(r.amount * ap.split_percent), 2) AS total_attributed_revenue_60d
      FROM account_partners ap
      JOIN partners p ON p.partner_id = ap.partner_id
      JOIN revenue_events r ON r.account_id = ap.account_id
      WHERE r.revenue_date >= date('now', '-60 day')
      GROUP BY p.partner_name
      ORDER BY total_attributed_revenue_60d DESC;
    """)
    if partner_impact.empty:
        st.info("No partner impact yet. Link a partner to a use case or create a manual AccountPartner.")
    else:
        st.dataframe(partner_impact, use_container_width=True)

    st.subheader("4) Attributed revenue (simple demo math)")

    ap_choices = {
        f"{row['account_name']} × {row['partner_name']} ({row['source']})": (row["account_id"], row["partner_id"], row["split_percent"])
        for _, row in ap.iterrows()
    }
    if not ap_choices:
        st.info("No AccountPartner relationships to show yet.")
    else:
        rel_choice = st.selectbox("Pick an AccountPartner relationship", list(ap_choices.keys()))
        account_id, partner_id, split_percent = ap_choices[rel_choice]

        rev = read_sql("""
          SELECT revenue_date, amount
          FROM revenue_events
          WHERE account_id = ?
          ORDER BY revenue_date DESC
          LIMIT 30;
        """, (account_id,))

        rev["attributed_amount"] = rev["amount"] * float(split_percent)

        c1, c2, c3 = st.columns(3)
        c1.metric("Split %", f"{split_percent*100:.0f}%")
        c2.metric("30d Account Revenue", f"{rev['amount'].sum():,.0f}")
        c3.metric("30d Attributed Revenue", f"{rev['attributed_amount'].sum():,.0f}")

        st.subheader("Why is this partner getting credit?")
        st.info(
            f"This partner is receiving credit because they are linked to this customer via an "
            f"AccountPartner relationship. Auto rows come from UseCasePartner rollups; manual rows are locked. "
            f"For this demo, we attribute revenue daily using: attributed_amount = account_amount × split_percent. "
            f"Here, split_percent = {split_percent*100:.0f}%."
        )

        st.dataframe(rev, use_container_width=True)
