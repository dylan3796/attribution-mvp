import json
import random
import sqlite3
import uuid
from typing import Optional, Tuple
import pandas as pd
import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Attribution MVP", layout="wide")

# Light theming to avoid plain white background
st.markdown(
    """
    <style>
    body {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8f0ff 50%, #fdfbfb 100%);
    }
    section.main > div {
        padding: 1.5rem 1.5rem 3rem 1.5rem;
    }
    .block-container {
        padding-top: 1.5rem;
    }
    .stTabs [role="tablist"] {
        gap: 0.25rem;
    }
    .stTabs [role="tab"] {
        border-radius: 12px;
        background: #f2f4f8;
        padding: 0.35rem 0.75rem;
        border: 1px solid #e0e6ef;
    }
    .stTabs [aria-selected="true"] {
        background: #d7e3ff;
        border-color: #b6ccff;
        color: #0b3ba7 !important;
        font-weight: 600;
    }
    .metric-card {
        background: rgba(255,255,255,0.75);
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1rem 1.25rem;
        box-shadow: 0 10px 30px rgba(12,33,80,0.07);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DB_PATH = "attribution.db"
SCHEMA_VERSION = "1.0"
DEFAULT_SETTINGS = {
    "enforce_split_cap": "true",  # whether account-level splits must sum to <= 100%
    "si_auto_split_mode": "live_share",  # Implementation (SI) auto split rule
    "si_fixed_percent": "20",  # used if mode is fixed_percent
    "default_split_influence": "10",
    "default_split_referral": "15",
    "default_split_isv": "10",
    "allow_manual_split_override": "false",
    "attribution_model": "hybrid",  # use_case_only | account_only | hybrid
    "schema_version": SCHEMA_VERSION,
    "account_rules": json.dumps([
        {
            "name": "Block SI below 50k estimated",
            "action": "deny",
            "when": {"partner_role": "Implementation (SI)", "max_estimated_value": 50000}
        },
        {
            "name": "Allow all fallback",
            "action": "allow",
            "when": {}
        }
    ], indent=2),
    "use_case_rules": json.dumps([
        {
            "name": "Allow all use cases",
            "action": "allow",
            "when": {}
        }
    ], indent=2),
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
    ensure_column("settings", "setting_value", "setting_value TEXT NOT NULL")

    # ensure settings table has defaults
    existing_settings = read_sql("SELECT setting_key FROM settings;")
    for key, val in DEFAULT_SETTINGS.items():
        if key not in existing_settings["setting_key"].tolist():
            run_sql("INSERT INTO settings(setting_key, setting_value) VALUES (?, ?);", (key, val))
    migrate_legacy_rules()

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

    def sample_estimated():
        # Heavily bias toward values near/below 5k, still allow higher tails
        if random.random() < 0.8:
            val = random.triangular(2000, 12000, 4500)
        else:
            val = random.triangular(12000, 100000, 15000)
        val = max(2000, min(100000, val))
        return int(round(val / 1000.0) * 1000)

    use_case_specs = [
        ("UC1", "A1", "Lakehouse Migration", "Discovery", (date.today() + timedelta(days=45)).isoformat()),
        ("UC2", "A1", "GenAI Support Bot", "Evaluation", (date.today() + timedelta(days=25)).isoformat()),
        ("UC3", "A2", "Claims Modernization", "Commit", (date.today() + timedelta(days=15)).isoformat()),
        ("UC4", "A3", "Fraud Detection", "Live", (date.today() - timedelta(days=10)).isoformat()),
        ("UC5", "A4", "Real-time Personalization", "Evaluation", (date.today() + timedelta(days=30)).isoformat()),
        ("UC6", "A5", "Manufacturing QA Analytics", "Discovery", (date.today() + timedelta(days=60)).isoformat()),
    ]
    use_cases = [(uc_id, acct, name, stage, sample_estimated(), tcd) for uc_id, acct, name, stage, tcd in use_case_specs]
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
    val = get_setting(key, str(default))
    val = str(val).lower()
    return val in ["true", "1", "yes", "on"]

def set_setting_bool(key: str, value: bool):
    set_setting(key, "true" if value else "false")

def get_setting(key: str, default: str) -> str:
    row = read_sql("SELECT setting_value FROM settings WHERE setting_key = ?;", (key,))
    if row.empty:
        return default
    return str(row.loc[0, "setting_value"])

def set_setting(key: str, value: str):
    run_sql("""
    INSERT INTO settings(setting_key, setting_value)
    VALUES (?, ?)
    ON CONFLICT(setting_key)
    DO UPDATE SET setting_value = excluded.setting_value;
    """, (key, value))

def should_enforce_split_cap() -> bool:
    return get_setting_bool("enforce_split_cap", default=True)

def compute_si_auto_split(use_case_value: float, account_live_total: float, account_all_total: float, mode: str) -> Tuple[Optional[float], str]:
    """
    Returns (split, explanation). split None means auto not applicable.
    """
    mode = mode or "live_share"
    if mode == "manual_only":
        return None, "Manual-only mode."
    if mode == "fixed_percent":
        fixed = float(get_setting("si_fixed_percent", "0")) / 100.0
        return min(max(fixed, 0.0), 1.0), "Fixed percent from settings."
    # live_share default
    base_total = account_live_total if account_live_total > 0 else account_all_total
    if base_total <= 0:
        return None, "No totals available to calculate share."
    split = min(use_case_value / base_total, 1.0) if base_total > 0 else None
    return split, "Use case value divided by account total."

def will_exceed_split_cap(account_id: str, partner_id: str, new_split: float) -> Tuple[bool, float]:
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

# ----------------------------
# Rule engine (simple conditions)
# ----------------------------
def migrate_legacy_rules():
    # migrate old key if present
    existing = read_sql("SELECT setting_key, setting_value FROM settings WHERE setting_key = 'rule_engine_rules';")
    if not existing.empty:
        val = existing.loc[0, "setting_value"]
        # only migrate if account_rules not already set
        if read_sql("SELECT setting_key FROM settings WHERE setting_key = 'account_rules';").empty:
            set_setting("account_rules", val)

def load_rules(key: str) -> list:
    try:
        raw = get_setting(key, DEFAULT_SETTINGS.get(key, "[]"))
        return json.loads(raw)
    except Exception:
        return []

def _matches_value(field_value, rule_value) -> bool:
    if isinstance(rule_value, list):
        return field_value in rule_value
    return field_value == rule_value


def rule_matches(rule_when: dict, ctx: dict) -> bool:
    if not rule_when:
        return True
    if "partner_role" in rule_when and not _matches_value(ctx.get("partner_role"), rule_when["partner_role"]):
        return False
    if "stage" in rule_when and not _matches_value(ctx.get("stage"), rule_when["stage"]):
        return False
    if "min_estimated_value" in rule_when and ctx.get("estimated_value") is not None:
        if ctx["estimated_value"] < float(rule_when["min_estimated_value"]):
            return False
    if "max_estimated_value" in rule_when and ctx.get("estimated_value") is not None:
        if ctx["estimated_value"] > float(rule_when["max_estimated_value"]):
            return False
    return True

def evaluate_rules(ctx: dict, key: str) -> Tuple[bool, str, bool, Optional[int]]:
    """
    Returns (allowed, message, matched_any_rule, matched_rule_index).
    If rules exist but none match, we block to avoid silent bypass.
    """
    rules = load_rules(key)
    matched = False
    for idx, rule in enumerate(rules):
        when = rule.get("when", {})
        if rule_matches(when, ctx):
            matched = True
            action = rule.get("action", "allow")
            name = rule.get("name", "Unnamed rule")
            if action == "deny":
                return False, f"Blocked by rule: {name}", matched, idx
            return True, f"Allowed by rule: {name}", matched, idx
    if rules:
        return False, "No matching rule; blocked by default. Add an 'allow' rule for these conditions.", matched, None
    return True, "No rules defined; allowed by default.", matched, None


def generate_rule_suggestion() -> dict:
    """
    Lightweight, local "AI-style" suggestion based on current data distribution.
    No external calls; just heuristic sampling to mimic an assistant.
    """
    use_cases = read_sql("SELECT stage, estimated_value FROM use_cases;")
    common_stage = "Commit"
    if not use_cases.empty and "stage" in use_cases:
        mode_stage = use_cases["stage"].mode(dropna=True)
        if not mode_stage.empty:
            common_stage = mode_stage.iloc[0]
    if use_cases.empty or "estimated_value" not in use_cases or use_cases["estimated_value"].dropna().empty:
        typical_val = 5000
    else:
        typical_val = float(use_cases["estimated_value"].dropna().median())
    # Nudge threshold above the typical value to focus on higher-risk items
    threshold = max(2000, min(100000, int(round((typical_val * 1.2) / 1000.0) * 1000)))
    role = random.choice(["Implementation (SI)", "Influence", "Referral", "ISV"])
    return {
        "name": f"AI suggestion: Gate {role} in {common_stage}",
        "action": "deny",
        "when": {
            "partner_role": role,
            "stage": common_stage,
            "min_estimated_value": threshold
        }
    }


def apply_rules_auto_assign(model: str) -> dict:
    """
    Apply current rules to existing use_case_partner links and auto-upsert account_partner splits.
    """
    if model == "use_case_only":
        return {"applied": 0, "blocked_rule": 0, "blocked_cap": 0, "skipped_manual": 0, "details": ["Account rollup disabled for current model."]}

    links = read_sql("""
        SELECT ucp.use_case_id, ucp.partner_id, ucp.partner_role,
               u.stage, u.estimated_value, u.account_id,
               a.account_name
        FROM use_case_partners ucp
        JOIN use_cases u ON u.use_case_id = ucp.use_case_id
        JOIN accounts a ON a.account_id = u.account_id;
    """)
    if links.empty:
        return {"applied": 0, "blocked_rule": 0, "blocked_cap": 0, "skipped_manual": 0, "details": ["No links to process."]}

    use_case_vals = read_sql("SELECT account_id, stage, estimated_value FROM use_cases;")
    live_totals = use_case_vals[use_case_vals["stage"] == "Live"].groupby("account_id")["estimated_value"].sum()
    all_totals = use_case_vals.groupby("account_id")["estimated_value"].sum()
    si_mode = get_setting("si_auto_split_mode", "live_share")
    defaults = {
        "Influence": float(get_setting("default_split_influence", "10")) / 100.0,
        "Referral": float(get_setting("default_split_referral", "15")) / 100.0,
        "ISV": float(get_setting("default_split_isv", "10")) / 100.0,
    }

    summary = {"applied": 0, "blocked_rule": 0, "blocked_cap": 0, "skipped_manual": 0, "details": []}
    for _, row in links.iterrows():
        allowed, msg, _, _ = evaluate_rules({
            "partner_role": row["partner_role"],
            "stage": row["stage"],
            "estimated_value": float(row["estimated_value"] or 0),
        }, key="account_rules")
        if not allowed:
            summary["blocked_rule"] += 1
            summary["details"].append(f"{row['account_name']} / {row['use_case_id']}: {msg}")
            continue
        split = defaults.get(row["partner_role"], 0.1)
        if row["partner_role"] == "Implementation (SI)":
            acct = row["account_id"]
            uc_value = float(row["estimated_value"] or 0)
            acct_live_total = float(live_totals.get(acct, 0))
            acct_all_total = float(all_totals.get(acct, 0))
            auto_split, _ = compute_si_auto_split(uc_value, acct_live_total, acct_all_total, si_mode)
            if auto_split is None:
                auto_split = float(get_setting("si_fixed_percent", "20")) / 100.0
            split = auto_split

        result = upsert_account_partner_from_use_case_partner(
            use_case_id=row["use_case_id"],
            partner_id=row["partner_id"],
            partner_role=row["partner_role"],
            split_percent=split
        )
        if result["status"] == "blocked_split_cap":
            summary["blocked_cap"] += 1
            summary["details"].append(f"{row['account_name']} / {row['use_case_id']}: blocked by split cap.")
        elif result["status"] == "skipped_manual":
            summary["skipped_manual"] += 1
        else:
            summary["applied"] += 1
    return summary


def render_apply_summary(summary: dict):
    msg = (
        f"Auto-applied: {summary.get('applied', 0)} | "
        f"Blocked by rules: {summary.get('blocked_rule', 0)} | "
        f"Blocked by split cap: {summary.get('blocked_cap', 0)} | "
        f"Skipped (manual sources): {summary.get('skipped_manual', 0)}"
    )
    total_touched = sum(summary.get(k, 0) for k in ["applied", "blocked_rule", "blocked_cap", "skipped_manual"])
    if total_touched == 0:
        st.warning(msg + " — no links processed. Ensure you have Use Case ↔ Partner links and at least one allow rule.")
    else:
        st.info(msg)
    details = summary.get("details", [])
    if details:
        st.caption("Notes: " + " | ".join(details[:5]))

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

# Light styling for readability
st.markdown(
    """
    <style>
    .small-cap {color:#6c757d; font-size:0.9rem;}
    .section-title {margin-top: 0.25rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Quick snapshots
accounts_df = read_sql("SELECT account_id, account_name FROM accounts;")
partners_df = read_sql("SELECT partner_id, partner_name FROM partners;")
use_cases_df = read_sql("SELECT use_case_id, account_id, stage FROM use_cases;")
ap_df = read_sql("SELECT account_id, partner_id FROM account_partners;")

st.caption("Transactional unit = Use Case between Partner & Customer. Auto rollup to AccountPartner + manual overrides.")
schema_stored = get_setting("schema_version", SCHEMA_VERSION)
if schema_stored != SCHEMA_VERSION:
    st.warning(
        f"Database schema version mismatch (found {schema_stored}, expected {SCHEMA_VERSION}). "
        "Use Admin → Reset demo data to refresh tables."
    )

# Tabs for clearer navigation
accounts = read_sql("SELECT account_id, account_name FROM accounts ORDER BY account_name;")

tabs = st.tabs([
    "Admin",
    "Account Partner 360",
    "Account Drilldown",
])

# --- Tab 1: Admin ---
with tabs[0]:
    st.subheader("Settings")
    st.caption("Configure guardrails and reset demo data.")

    settings_left, settings_right = st.columns([2, 1])
    with settings_left:
        enforce_default = should_enforce_split_cap()
        si_mode_default = get_setting("si_auto_split_mode", "live_share")
        si_fixed_default = float(get_setting("si_fixed_percent", "20"))
        inf_default = float(get_setting("default_split_influence", "10"))
        ref_default = float(get_setting("default_split_referral", "15"))
        isv_default = float(get_setting("default_split_isv", "10"))
        with st.form("settings_form"):
            enforce_cap = st.checkbox(
                "Enforce account split cap (≤ 100% total per account)",
                value=enforce_default,
                help="When ON, adding or updating splits will be blocked if the account's total would exceed 100%. Turn OFF to allow totals > 100%.",
            )
            si_mode = st.selectbox(
                "Implementation (SI) auto-split rule",
                ["live_share", "fixed_percent", "manual_only"],
                index=["live_share", "fixed_percent", "manual_only"].index(si_mode_default if si_mode_default in ["live_share", "fixed_percent", "manual_only"] else "live_share"),
                help="live_share = auto split based on use case value vs account totals. fixed_percent = use a set % for SI. manual_only = always set manually.",
            )
            if si_mode == "fixed_percent":
                si_fixed = st.slider("SI fixed percent", 0, 100, int(si_fixed_default))
            else:
                si_fixed = si_fixed_default
            col_defaults = st.columns(3)
            with col_defaults[0]:
                inf_split = st.slider("Default % Influence", 0, 100, int(inf_default))
            with col_defaults[1]:
                ref_split = st.slider("Default % Referral", 0, 100, int(ref_default))
            with col_defaults[2]:
                isv_split = st.slider("Default % ISV", 0, 100, int(isv_default))
            allow_manual = st.checkbox("Allow manual split override", value=get_setting_bool("allow_manual_split_override", False), help="When off, splits are auto-assigned from rules/defaults without sliders.")
            save_settings = st.form_submit_button("Save settings")
            if save_settings:
                set_setting_bool("enforce_split_cap", enforce_cap)
                set_setting("si_auto_split_mode", si_mode)
                set_setting("si_fixed_percent", str(si_fixed))
                set_setting("default_split_influence", str(inf_split))
                set_setting("default_split_referral", str(ref_split))
                set_setting("default_split_isv", str(isv_split))
                set_setting_bool("allow_manual_split_override", allow_manual)
                st.success(f"Saved. Enforce split cap = {'ON' if enforce_cap else 'OFF'}.")

    with settings_right:
        st.caption("Admin")
        if st.button("Reset demo data (start fresh)"):
            reset_demo()
            st.success("Reset complete. Refresh the page.")

    st.markdown("---")
    st.markdown('<a id="rule-builder"></a>', unsafe_allow_html=True)
    st.subheader("Attribution model")
    st.caption("Pick the simplest path: use-case-only (no account splits), account-only, or hybrid.")
    model_labels = {
        "use_case_only": "Use-Case Only (no account splits)",
        "account_only": "Account Consumption Only (account splits from links)",
        "hybrid": "Hybrid (use-case links + account splits)"
    }
    model = st.radio("Model", list(model_labels.keys()), format_func=lambda k: model_labels[k], index=["use_case_only", "account_only", "hybrid"].index(get_setting("attribution_model", "hybrid")))
    set_setting("attribution_model", model)
    st.info(f"Model: {model_labels[model]}")

    def render_rule_section(title: str, key: str, enabled: bool, applies_to_account: bool):
        st.markdown(f"### {title}")
        if not enabled:
            st.warning("Disabled for current model.")
            return
        rules = load_rules(key)
        if f"ai_rule_suggestion_{key}" not in st.session_state:
            st.session_state[f"ai_rule_suggestion_{key}"] = None
        preview_data = read_sql("""
            SELECT ucp.partner_role, u.stage, u.estimated_value
            FROM use_case_partners ucp
            JOIN use_cases u ON u.use_case_id = ucp.use_case_id;
        """)
        with st.expander("Current rules", expanded=False):
            if rules:
                rule_rows = []
                for r in rules:
                    when = r.get("when", {})
                    rule_rows.append({
                        "Name": r.get("name", ""),
                        "Action": r.get("action", "allow"),
                        "Partner role": when.get("partner_role", "Any"),
                        "Stage": when.get("stage", "Any"),
                        "Min est. value": when.get("min_estimated_value", ""),
                        "Max est. value": when.get("max_estimated_value", ""),
                    })
                st.dataframe(pd.DataFrame(rule_rows), use_container_width=True)
            else:
                st.info("No rules yet. Add one below.")

        add_col1, add_col2 = st.columns([3, 1])
        with add_col1:
            with st.expander("Add or edit rule", expanded=True):
                rule_name = st.text_input("Rule name", value="Custom rule", key=f"name_{key}")
                action = st.selectbox("Action", ["allow", "deny"], key=f"action_{key}")
                partner_role_choice = st.multiselect("Partner role(s)", ["Implementation (SI)", "Influence", "Referral", "ISV"], default=[], key=f"roles_{key}")
                stage_choice = st.multiselect("Stage(s)", ["Discovery", "Evaluation", "Commit", "Live"], default=[], key=f"stages_{key}")
                use_range = st.checkbox("Set estimated value range", value=False, key=f"use_range_{key}")
                min_val, max_val = (0.0, 100000.0)
                if use_range:
                    min_val, max_val = st.slider("Estimated value range", 0, 100000, (0, 100000), step=1000, key=f"range_{key}")
                if st.button("Add rule", key=f"add_rule_{key}"):
                    if use_range and min_val > max_val:
                        st.error("Min cannot be greater than max.")
                    else:
                        new_rule = {
                            "name": rule_name,
                            "action": action,
                            "when": {}
                        }
                        if partner_role_choice:
                            new_rule["when"]["partner_role"] = partner_role_choice if len(partner_role_choice) > 1 else partner_role_choice[0]
                        if stage_choice:
                            new_rule["when"]["stage"] = stage_choice if len(stage_choice) > 1 else stage_choice[0]
                        if use_range:
                            new_rule["when"]["min_estimated_value"] = min_val
                            new_rule["when"]["max_estimated_value"] = max_val
                        if not partner_role_choice and not stage_choice and not use_range and action == "deny":
                            st.warning("Deny-all rule would block everything. Consider narrowing conditions or add an allow-all catch-all below.")
                        updated = rules + [new_rule]
                        set_setting(key, json.dumps(updated, indent=2))
                        st.success("Rule added.")
                        if not preview_data.empty:
                            match_count = sum(rule_matches(new_rule.get("when", {}), row) for _, row in preview_data.iterrows())
                            st.info(f"Would match {match_count}/{len(preview_data)} existing links.")
                        if applies_to_account:
                            render_apply_summary(apply_rules_auto_assign(model))
                if rules:
                    edit_idx = st.selectbox("Select rule to edit", list(range(len(rules))), format_func=lambda i: rules[i].get("name", f"Rule {i+1}"), key=f"edit_idx_{key}")
                    to_edit = rules[edit_idx]
                    e_name = st.text_input("Edit name", value=to_edit.get("name", ""), key=f"edit_name_{key}")
                    e_action = st.selectbox("Edit action", ["allow", "deny"], index=["allow", "deny"].index(to_edit.get("action", "allow")), key=f"edit_action_{key}")
                    e_roles = to_edit.get("when", {}).get("partner_role", [])
                    if isinstance(e_roles, str):
                        e_roles = [e_roles]
                    e_stages = to_edit.get("when", {}).get("stage", [])
                    if isinstance(e_stages, str):
                        e_stages = [e_stages]
                    e_roles_sel = st.multiselect("Edit partner role(s)", ["Implementation (SI)", "Influence", "Referral", "ISV"], default=e_roles, key=f"edit_roles_{key}")
                    e_stages_sel = st.multiselect("Edit stage(s)", ["Discovery", "Evaluation", "Commit", "Live"], default=e_stages, key=f"edit_stages_{key}")
                    e_range_enabled = "min_estimated_value" in to_edit.get("when", {}) or "max_estimated_value" in to_edit.get("when", {})
                    e_min = float(to_edit.get("when", {}).get("min_estimated_value", 0))
                    e_max = float(to_edit.get("when", {}).get("max_estimated_value", 100000))
                    e_use_range = st.checkbox("Edit estimated value range", value=e_range_enabled, key=f"edit_range_{key}")
                    if e_use_range:
                        e_min, e_max = st.slider("Edit estimated value range", 0, 100000, (int(e_min), int(e_max)), step=1000, key=f"edit_slider_{key}")
                    if st.button("Save edits", key=f"save_edits_{key}"):
                        updated = []
                        for i, r in enumerate(rules):
                            if i != edit_idx:
                                updated.append(r)
                                continue
                            new_r = {"name": e_name, "action": e_action, "when": {}}
                            if e_roles_sel:
                                new_r["when"]["partner_role"] = e_roles_sel if len(e_roles_sel) > 1 else e_roles_sel[0]
                            if e_stages_sel:
                                new_r["when"]["stage"] = e_stages_sel if len(e_stages_sel) > 1 else e_stages_sel[0]
                            if e_use_range:
                                new_r["when"]["min_estimated_value"] = e_min
                                new_r["when"]["max_estimated_value"] = e_max
                            updated.append(new_r)
                        set_setting(key, json.dumps(updated, indent=2))
                        st.success("Rule updated.")
                        if applies_to_account:
                            render_apply_summary(apply_rules_auto_assign(model))
        with add_col2:
            with st.expander("Quick actions", expanded=False):
                if rules:
                    delete_idx = st.selectbox("Select rule to delete", list(range(len(rules))), format_func=lambda i: rules[i].get("name", f"Rule {i+1}"), key=f"delete_idx_{key}")
                    if st.button("Delete selected rule", key=f"delete_rule_{key}"):
                        updated = [r for i, r in enumerate(rules) if i != delete_idx]
                        set_setting(key, json.dumps(updated, indent=2))
                        st.success("Rule deleted.")
                if st.button("Add allow-all", key=f"allow_all_{key}"):
                    updated = rules + [{"name": "Allow all", "action": "allow", "when": {}}]
                    set_setting(key, json.dumps(updated, indent=2))
                    st.success("Allow-all rule added.")
                    if applies_to_account:
                        render_apply_summary(apply_rules_auto_assign(model))
                if st.button("Add block SI in Commit", key=f"block_template_{key}"):
                    updated = rules + [{
                        "name": "Block SI in Commit",
                        "action": "deny",
                        "when": {"partner_role": "Implementation (SI)", "stage": "Commit"}
                    }]
                    set_setting(key, json.dumps(updated, indent=2))
                    st.success("Template rule added.")
                    if applies_to_account:
                        render_apply_summary(apply_rules_auto_assign(model))
                suggestion = st.session_state.get(f"ai_rule_suggestion_{key}")
                if st.button("Generate suggestion", key=f"gen_suggest_{key}"):
                    st.session_state[f"ai_rule_suggestion_{key}"] = generate_rule_suggestion()
                if suggestion:
                    st.code(json.dumps(suggestion, indent=2), language="json")
                    if st.button("Use suggestion", key=f"use_suggest_{key}"):
                        updated = rules + [suggestion]
                        set_setting(key, json.dumps(updated, indent=2))
                        st.success("Suggested rule added.")
                        st.session_state[f"ai_rule_suggestion_{key}"] = None

        with st.expander("Preview / Apply", expanded=False):
            if st.button("Preview matches", key=f"preview_{key}"):
                if preview_data.empty:
                    st.info("No existing links to preview.")
                else:
                    matches = 0
                    for _, r in preview_data.iterrows():
                        if evaluate_rules({
                            "partner_role": r["partner_role"],
                            "stage": r["stage"],
                            "estimated_value": r["estimated_value"],
                        }, key=key)[0]:
                            matches += 1
                    st.info(f"Would affect {matches} of {len(preview_data)} existing links.")
            if applies_to_account and st.button("Apply to account splits now", key=f"apply_{key}"):
                render_apply_summary(apply_rules_auto_assign(model))
            elif not applies_to_account:
                st.caption("Use-case rules gate link creation. Account splits are unaffected.")

    render_rule_section("Use Case Rules (per-link gating)", key="use_case_rules", enabled=model in ["use_case_only", "hybrid"], applies_to_account=False)
    render_rule_section("Account Rules (roll up to account splits)", key="account_rules", enabled=model in ["account_only", "hybrid"], applies_to_account=True)

# --- Tab 2: Relationships ---
with tabs[1]:
    st.subheader("Catalog & links")
    model = get_setting("attribution_model", "hybrid")
    model_labels_local = {
        "use_case_only": "Use-Case Only (no account splits)",
        "account_only": "Account Consumption Only (account splits from links)",
        "hybrid": "Hybrid (use-case links + account splits)"
    }
    st.caption("Accounts, use cases, and partner links in one place. Imported CRM links will appear here.")
    st.info(f"Attribution model: {model_labels_local.get(model, model)}")
    filter_cols = st.columns(3)
    with filter_cols[0]:
        account_filter = st.selectbox("Filter by account", ["All"] + [f"{row['account_name']} ({row['account_id']})" for _, row in accounts.iterrows()])
    with filter_cols[1]:
        stage_filter = st.selectbox("Filter by stage", ["All", "Discovery", "Evaluation", "Commit", "Live"])
    with filter_cols[2]:
        partner_filter = st.selectbox("Filter by partner", ["All"] + [row["partner_name"] for _, row in read_sql("SELECT partner_name FROM partners ORDER BY partner_name;").iterrows()])

    use_cases = read_sql("""
        SELECT u.use_case_id, u.use_case_name, u.stage, u.estimated_value, u.target_close_date, a.account_name, a.account_id
        FROM use_cases u
        JOIN accounts a ON a.account_id = u.account_id
        ORDER BY a.account_name, u.use_case_name;
    """)
    manual_override_allowed = get_setting_bool("allow_manual_split_override", False)
    if not manual_override_allowed:
        st.caption("Auto-assign mode is ON. Enable manual overrides in Admin if you want sliders.")
    if account_filter != "All":
        sel_id = account_filter.split("(")[-1].rstrip(")")
        use_cases = use_cases[use_cases["account_id"] == sel_id]
    if stage_filter != "All":
        use_cases = use_cases[use_cases["stage"].str.lower() == stage_filter.lower()]
    st.markdown("**Filtered totals**")
    # Apply filters to metrics within this tab and update top-level placeholders
    filtered_accounts = accounts_df
    filtered_partners = partners_df
    filtered_aps = ap_df
    if account_filter != "All":
        filtered_accounts = filtered_accounts[filtered_accounts["account_id"] == sel_id]
        filtered_aps = filtered_aps[filtered_aps["account_id"] == sel_id]
        filtered_use_cases = use_cases_df[use_cases_df["account_id"] == sel_id]
    else:
        filtered_use_cases = use_cases_df
    if partner_filter != "All":
        partner_ids = partners_df[partners_df["partner_name"] == partner_filter]["partner_id"]
        filtered_partners = partners_df[partners_df["partner_name"] == partner_filter]
        filtered_aps = filtered_aps[filtered_aps["partner_id"].isin(partner_ids)]
    if stage_filter != "All":
        uc_filtered_stage = read_sql("""
            SELECT use_case_id, account_id
            FROM use_cases
            WHERE LOWER(stage) = ?;
        """, (stage_filter.lower(),))
        filtered_use_cases = filtered_use_cases.merge(uc_filtered_stage, on=["use_case_id", "account_id"], how="inner")
        filtered_aps = filtered_aps[filtered_aps["account_id"].isin(filtered_use_cases["account_id"])]

    metrics_row = st.columns(4)
    metrics_row[0].metric("Accounts", f"{len(filtered_accounts)}")
    metrics_row[1].metric("Partners", f"{len(filtered_partners)}")
    metrics_row[2].metric("Use cases", f"{len(filtered_use_cases)}")
    metrics_row[3].metric("AccountPartner links", f"{len(filtered_aps)}")

    st.markdown("**Use cases**")
    if use_cases.empty:
        st.info("No use cases available. Add them to the database to enable attribution.")
    else:
        st.dataframe(use_cases, use_container_width=True)

    st.markdown("---")
    st.subheader("Link partner to use case (auto-rollup to AccountPartner)")
    partners = read_sql("SELECT partner_id, partner_name FROM partners ORDER BY partner_name;")

    if use_cases.empty or partners.empty:
        st.info("Need at least one use case and partner to create a UseCasePartner.")
    else:
        si_auto_mode = get_setting("si_auto_split_mode", "live_share")
        inf_default = float(get_setting("default_split_influence", "10"))
        ref_default = float(get_setting("default_split_referral", "15"))
        isv_default = float(get_setting("default_split_isv", "10"))
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

        # Auto-calculation rule for Implementation partners: allocate split based on use case's share of live or total value.
        selected_uc = uc_label_map[uc_choice]
        uc_row = use_cases[use_cases["use_case_id"] == selected_uc].iloc[0]
        uc_value = float(uc_row["estimated_value"] or 0)
        account_live_total = use_cases[
            (use_cases["account_id"] == uc_row["account_id"])
            & (use_cases["stage"].str.lower() == "live")
            & use_cases["estimated_value"].notnull()
        ]["estimated_value"].sum()
        account_all_total = use_cases[
            (use_cases["account_id"] == uc_row["account_id"])
            & use_cases["estimated_value"].notnull()
        ]["estimated_value"].sum()
        base_total = account_live_total if account_live_total > 0 else account_all_total

        auto_split = None
        if role_choice == "Implementation (SI)":
            auto_split, auto_reason = compute_si_auto_split(uc_value, account_live_total, account_all_total, si_auto_mode)
            if auto_split is not None:
                source_label = "live total" if account_live_total > 0 else "total estimated (no live use cases)"
                st.info(
                    f"Auto split for SI: use case value {uc_value:,.0f} / {source_label} {base_total:,.0f} "
                    f"= {auto_split*100:.0f}% ({auto_reason})"
                )
                st.metric("Applied split %", f"{auto_split*100:.0f}%", help="Auto-applied based on Implementation (SI) rule.")
                split = auto_split
                if manual_override_allowed:
                    use_override = st.checkbox("Override auto-calculated split", value=False)
                    if use_override:
                        split = st.slider("Custom split %", 0, 100, int(auto_split * 100)) / 100.0
            else:
                if si_auto_mode == "manual_only":
                    st.warning("Manual-only mode: set the split for Implementation (SI).")
                    default_manual = int(float(get_setting("si_fixed_percent", "20")))
                    split = st.slider("Split % for account-level credit", 0, 100, default_manual) / 100.0
                else:
                    fallback = float(get_setting("si_fixed_percent", "20")) / 100.0
                    st.warning(f"Auto split not available for this SI rule/data. Applying fallback {fallback*100:.0f}% (change in Admin settings).")
                    split = fallback
                    if manual_override_allowed:
                        split = st.slider("Split % for account-level credit", 0, 100, int(fallback * 100)) / 100.0
        else:
            default_map = {
                "Influence": inf_default,
                "Referral": ref_default,
                "ISV": isv_default,
            }
            default_val = int(default_map.get(role_choice, 10))
            if manual_override_allowed:
                split = st.slider("Split % for account-level credit", 0, 100, default_val) / 100.0
            else:
                split = default_val / 100.0
                st.info(f"Auto-assigned {default_val}% based on defaults. Enable manual override in Admin to customize.")

        if st.button("Save use case ↔ partner (auto rollup)"):
            uc_allowed, uc_msg, _, uc_rule_idx = evaluate_rules({
                "partner_role": role_choice,
                "stage": str(uc_row["stage"]) if pd.notnull(uc_row["stage"]) else None,
                "estimated_value": uc_value,
            }, key="use_case_rules")
            if not uc_allowed:
                st.error(f"Use case rule blocked: {uc_msg}")
            else:
                uc_link = " [View rule](#rule-builder)" if uc_rule_idx is not None else ""
                st.info(f"Use case allowed: {uc_msg}{uc_link}")
                # Always save the use case ↔ partner link
                today = date.today().isoformat()
                run_sql("""
                INSERT INTO use_case_partners(use_case_id, partner_id, partner_role, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(use_case_id, partner_id)
                DO UPDATE SET partner_role = excluded.partner_role;
                """, (uc_label_map[uc_choice], p_label_map[p_choice], role_choice, today))
                if model in ["account_only", "hybrid"]:
                    acct_allowed, acct_msg, _, acct_rule_idx = evaluate_rules({
                        "partner_role": role_choice,
                        "stage": str(uc_row["stage"]) if pd.notnull(uc_row["stage"]) else None,
                        "estimated_value": uc_value,
                    }, key="account_rules")
                    if not acct_allowed:
                        st.error(f"Account split blocked: {acct_msg}")
                    else:
                        acct_link = " [View rule](#rule-builder)" if acct_rule_idx is not None else ""
                        st.info(f"Account rules passed: {acct_msg}{acct_link}")
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
                            st.success(f"Saved. UseCasePartner created/updated AND AccountPartner auto-upserted at {split*100:.0f}% split.")
                else:
                    st.success("UseCasePartner saved. Account rollup skipped (use-case-only model).")

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
    if account_filter != "All":
        links = links[links["account_name"].str.contains(account_filter.split(" (")[0])]
    if stage_filter != "All":
        links = links[links["stage"].str.lower() == stage_filter.lower()]
    if partner_filter != "All":
        links = links[links["partner_name"] == partner_filter]
    if not links.empty:
        st.caption("Use Case ↔ Partner links (auto rollup sources)")
        st.dataframe(links, use_container_width=True)

    st.markdown("---")
    st.subheader("AccountPartner relationships (auto + manual)")
    ap = read_sql("""
      SELECT ap.account_id, a.account_name, ap.partner_id, p.partner_name, ap.split_percent, ap.first_seen, ap.last_seen, ap.source
      FROM account_partners ap
      JOIN accounts a ON a.account_id = ap.account_id
      JOIN partners p ON p.partner_id = ap.partner_id
      ORDER BY a.account_name, p.partner_name;
    """)
    if account_filter != "All":
        ap = ap[ap["account_name"].str.contains(account_filter.split(" (")[0])]
    if partner_filter != "All":
        ap = ap[ap["partner_name"] == partner_filter]
    # stage filter indirectly via use_cases joined to account partners
    if stage_filter != "All":
        uc_stage = read_sql("""
            SELECT DISTINCT ap.account_id, ap.partner_id
            FROM account_partners ap
            JOIN use_cases u ON u.account_id = ap.account_id
            WHERE LOWER(u.stage) = ?;
        """, (stage_filter.lower(),))
        key_pairs = set(zip(uc_stage["account_id"], uc_stage["partner_id"]))
        ap = ap[[ (row["account_id"], row["partner_id"]) in key_pairs for _, row in ap.iterrows() ]]

    if ap.empty:
        st.info("No AccountPartner relationships yet. Auto-create from a UseCasePartner or add manually below.")
    else:
        st.dataframe(ap, use_container_width=True)

    st.subheader("Manual AccountPartner (override or add)")
    partners = read_sql("SELECT partner_id, partner_name FROM partners ORDER BY partner_name;")  # ensure fresh
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

    st.markdown("---")
    st.subheader("Partner impact (60d snapshot)")
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
    if partner_filter != "All":
        partner_impact = partner_impact[partner_impact["partner_name"] == partner_filter]
    if partner_impact.empty:
        st.info("No partner impact yet. Link a partner to a use case or create a manual AccountPartner.")
    else:
        st.dataframe(partner_impact, use_container_width=True)

# --- Tab 3: Account Drilldown ---
with tabs[2]:
    st.subheader("Account drilldown (use cases + revenue)")
    if accounts.empty:
        st.info("No accounts available.")
    else:
        acct_map = {f"{row['account_name']} ({row['account_id']})": row["account_id"] for _, row in accounts.iterrows()}
        acct_choice = st.selectbox("Account", list(acct_map.keys()))
        selected_account_id = acct_map[acct_choice]

        st.caption("Review use cases, linked partners, and revenue for this account.")

        acct_use_cases = read_sql("""
            SELECT use_case_id, use_case_name, stage, estimated_value, target_close_date
            FROM use_cases
            WHERE account_id = ?
            ORDER BY use_case_name;
        """, (selected_account_id,))
        st.markdown("**Use cases**")
        if acct_use_cases.empty:
            st.info("No use cases for this account.")
        else:
            st.dataframe(acct_use_cases, use_container_width=True)

        acct_ap = read_sql("""
          SELECT ap.partner_id, p.partner_name, ap.split_percent, ap.first_seen, ap.last_seen, ap.source
          FROM account_partners ap
          JOIN partners p ON p.partner_id = ap.partner_id
          WHERE ap.account_id = ?
          ORDER BY p.partner_name;
        """, (selected_account_id,))
        st.markdown("**AccountPartner links**")
        if acct_ap.empty:
            st.info("No partners linked to this account yet.")
        else:
            st.dataframe(acct_ap, use_container_width=True)

        rev = read_sql("""
          SELECT revenue_date, amount
          FROM revenue_events
          WHERE account_id = ?
          AND revenue_date >= date('now', '-30 day')
          ORDER BY revenue_date DESC;
        """, (selected_account_id,))
        total_rev = float(rev["amount"].sum()) if not rev.empty else 0.0

        attr_by_partner = read_sql("""
          SELECT
            p.partner_name,
            ap.split_percent,
            ROUND(SUM(r.amount * ap.split_percent), 2) AS attributed_amount
          FROM account_partners ap
          JOIN partners p ON p.partner_id = ap.partner_id
          JOIN revenue_events r ON r.account_id = ap.account_id
          WHERE ap.account_id = ?
            AND r.revenue_date >= date('now', '-30 day')
          GROUP BY p.partner_name, ap.split_percent
          ORDER BY attributed_amount DESC;
        """, (selected_account_id,))
        total_attr = float(attr_by_partner["attributed_amount"].sum()) if not attr_by_partner.empty else 0.0

        c1, c2 = st.columns(2)
        c1.metric("30d Account Revenue", f"{total_rev:,.0f}")
        c2.metric("30d Attributed Revenue", f"{total_attr:,.0f}")

        st.markdown("**Attributed revenue by partner (30d)**")
        if attr_by_partner.empty:
            st.info("No partner-linked revenue in the last 30 days.")
        else:
            st.dataframe(attr_by_partner, use_container_width=True)

        st.markdown("**Revenue events (30d)**")
        if rev.empty:
            st.info("No revenue events in the last 30 days.")
        else:
            st.dataframe(rev, use_container_width=True)
