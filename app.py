import json
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

# Import our new modules
from config import DB_PATH, LOG_LEVEL, LOG_FILE
from db import Database
from rules import RuleEngine
from attribution import AttributionEngine
from ai import AIFeatures
from models import PARTNER_ROLES, SCHEMA_VERSION, DEFAULT_SETTINGS
from utils import (
    safe_json_loads,
    dataframe_to_csv_download,
    setup_logging,
    render_apply_summary_dict
)
from dashboards import (
    create_revenue_over_time_chart,
    create_partner_performance_bar_chart,
    create_attribution_pie_chart,
    create_pipeline_funnel_chart,
    create_account_health_gauge,
    create_attribution_waterfall,
    create_partner_role_distribution
)
from exports import (
    export_to_csv,
    export_to_excel,
    generate_pdf_report,
    create_partner_performance_report,
    create_account_drilldown_report
)
from bulk_operations import (
    import_accounts_from_csv,
    import_partners_from_csv,
    import_use_cases_from_csv,
    import_use_case_partners_from_csv,
    export_all_data,
    get_import_template
)

# Setup logging
setup_logging(LOG_LEVEL, LOG_FILE)

# Initialize database and engines
db = Database(DB_PATH)
rule_engine = RuleEngine(db)
attribution_engine = AttributionEngine(db, rule_engine)
ai_features = AIFeatures(db)


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
    "enable_use_case_rules": "true",
    "enable_account_rollup": "true",
    "use_case_tag_source": "hybrid",
    "prompt_rule_conversion": "Convert this rule description into JSON with keys name, action (allow/deny), when (partner_role?, stage?, min_estimated_value?, max_estimated_value?). Only return JSON.",
    "prompt_relationship_summary": "Summarize account relationships with 3 concise bullets: health, risks, next steps.",
    "prompt_ai_recommendations": "Recommend partner attributions. Return JSON list of {partner_id, recommended_role, recommended_split_percent, confidence, reasons}.",
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

PARTNER_ROLES = ["Implementation (SI)", "Influence", "Referral", "ISV"]



# Initialize database
db.init_db()
db.seed_data_if_empty()

# Helper function wrappers for compatibility
def read_sql(sql: str, params: tuple = ()) -> pd.DataFrame:
    return db.read_sql(sql, params)

def run_sql(sql: str, params: tuple = ()):
    db.run_sql(sql, params)

def get_setting(key: str, default: str) -> str:
    return db.get_setting(key, default)

def set_setting(key: str, value: str):
    db.set_setting(key, value)

def get_setting_bool(key: str, default: bool) -> bool:
    return db.get_setting_bool(key, default)

def set_setting_bool(key: str, value: bool):
    db.set_setting_bool(key, value)

def should_enforce_split_cap() -> bool:
    return attribution_engine.should_enforce_split_cap()

def will_exceed_split_cap(account_id: str, partner_id: str, new_split: float):
    return attribution_engine.will_exceed_split_cap(account_id, partner_id, new_split)

def compute_si_auto_split(use_case_value: float, account_live_total: float, account_all_total: float, mode: str):
    return attribution_engine.compute_si_auto_split(use_case_value, account_live_total, account_all_total, mode)

def upsert_account_partner_from_use_case_partner(use_case_id: str, partner_id: str, partner_role: str, split_percent: float):
    result = attribution_engine.upsert_account_partner_from_use_case_partner(use_case_id, partner_id, partner_role, split_percent)
    return {"status": result.status, "account_id": result.account_id, "total_with_new": result.total_with_new}

def upsert_manual_account_partner(account_id: str, partner_id: str, split_percent: float):
    result = attribution_engine.upsert_manual_account_partner(account_id, partner_id, split_percent)
    return {"status": result.status, "account_id": result.account_id, "total_with_new": result.total_with_new}

def apply_rules_auto_assign(account_rollup_enabled: bool):
    summary = attribution_engine.apply_rules_auto_assign(account_rollup_enabled)
    return {
        "applied": summary.applied,
        "blocked_rule": summary.blocked_rule,
        "blocked_cap": summary.blocked_cap,
        "skipped_manual": summary.skipped_manual,
        "details": summary.details
    }

def recompute_attribution_ledger(days: int = 30):
    result = attribution_engine.recompute_attribution_ledger(days)
    return {"inserted": result.inserted, "skipped": result.skipped, "blocked": result.blocked}

def simulate_rule_impact(key: str, days: int = 60):
    result = attribution_engine.simulate_rule_impact(key, days)
    return {
        "target": result.target,
        "lookback_days": result.lookback_days,
        "checked": result.checked,
        "allowed": result.allowed,
        "blocked": result.blocked,
        "no_context": result.no_context,
        "revenue_at_risk": result.revenue_at_risk,
        "estimated_value_blocked": result.estimated_value_blocked,
        "details": result.details
    }

def recompute_explanations(account_id: str):
    return attribution_engine.recompute_explanations(account_id)

def create_use_case(account_id: str, use_case_name: str, stage: str, estimated_value: float, target_close_date: str, tag_source: str = "app"):
    return attribution_engine.create_use_case(account_id, use_case_name, stage, estimated_value, target_close_date, tag_source)

def reset_demo():
    db.reset_demo()

def load_rules(key: str):
    return rule_engine.load_rules(key)

def evaluate_rules(ctx: dict, key: str):
    result = rule_engine.evaluate_rules(ctx, key)
    return (result.allowed, result.message, result.matched_any_rule, result.matched_rule_index, result.rule_name)

def generate_rule_suggestion():
    return rule_engine.generate_rule_suggestion()

def validate_rule_obj(rule: dict) -> bool:
    return rule_engine.validate_rule_obj(rule)

def convert_nl_to_rule(text: str):
    return ai_features.convert_nl_to_rule(text)

def generate_relationship_summary(account_id: str):
    return ai_features.generate_relationship_summary(account_id)

def generate_ai_recommendations(account_id: str):
    return ai_features.generate_ai_recommendations(account_id)

def apply_recommendations(account_id: str, recs: list):
    return ai_features.apply_recommendations(account_id, recs, attribution_engine)

def infer_partner_role(account_name: str, use_case_name: str, partner_name: str, context: str):
    return ai_features.infer_partner_role(account_name, use_case_name, partner_name, context)

def render_apply_summary(summary: dict):
    msg = render_apply_summary_dict(summary)
    total_touched = sum(summary.get(k, 0) for k in ["applied", "blocked_rule", "blocked_cap", "skipped_manual"])
    if total_touched == 0:
        st.warning(msg)
    else:
        st.info(msg)
    details = summary.get("details", [])
    if details:
        st.caption("Notes: " + " | ".join(details[:5]))

# ----------------------------
# App
# ----------------------------
# Already initialized in the wrapper functions section above
# The db object is initialized and ready to use

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
if "ledger_bootstrap" not in st.session_state:
    recompute_attribution_ledger(30)
    st.session_state["ledger_bootstrap"] = True

# Tabs for clearer navigation
accounts = read_sql("SELECT account_id, account_name FROM accounts ORDER BY account_name;")

tabs = st.tabs([
    "Dashboard",
    "Admin",
    "Account Partner 360",
    "Account Drilldown",
    "Relationship Summary (AI)",
    "Audit Trail",
])

# --- Tab 0: Dashboard ---
with tabs[0]:
    st.title("Attribution Dashboard")
    st.caption("Executive overview of partner attribution performance and metrics")

    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        dashboard_days = st.selectbox(
            "Time Period",
            [7, 30, 60, 90, 180],
            index=1,
            format_func=lambda x: f"Last {x} days"
        )
    with col2:
        refresh_dashboard = st.button("Refresh Dashboard", type="primary")

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=dashboard_days)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # Fetch dashboard data
    with st.spinner("Loading dashboard data..."):
        # Revenue data
        revenue_df = read_sql("""
            SELECT revenue_date, amount, account_id
            FROM revenue_events
            WHERE revenue_date BETWEEN ? AND ?
            ORDER BY revenue_date;
        """, (start_str, end_str))

        # Attribution data
        attribution_df = read_sql("""
            SELECT
                p.partner_name,
                p.partner_id,
                SUM(ae.attributed_amount) AS attributed_amount,
                AVG(ae.split_percent) AS avg_split_percent,
                COUNT(DISTINCT ae.account_id) AS accounts_influenced
            FROM attribution_events ae
            JOIN partners p ON p.partner_id = ae.actor_id
            WHERE ae.revenue_date BETWEEN ? AND ?
            GROUP BY p.partner_name, p.partner_id
            ORDER BY attributed_amount DESC;
        """, (start_str, end_str))

        # Use cases by stage
        use_cases_df = read_sql("""
            SELECT use_case_id, use_case_name, stage, estimated_value, target_close_date, account_id
            FROM use_cases
            WHERE estimated_value IS NOT NULL;
        """)

        # Partner roles distribution
        partner_roles_df = read_sql("""
            SELECT partner_role, use_case_id, partner_id
            FROM use_case_partners;
        """)

        # Account health metrics
        account_health_df = read_sql("""
            SELECT
                a.account_id,
                a.account_name,
                COUNT(DISTINCT u.use_case_id) AS active_use_cases,
                COUNT(DISTINCT ap.partner_id) AS total_partners,
                COALESCE(SUM(CASE WHEN u.stage = 'Live' THEN u.estimated_value ELSE 0 END), 0) AS live_value
            FROM accounts a
            LEFT JOIN use_cases u ON u.account_id = a.account_id
            LEFT JOIN account_partners ap ON ap.account_id = a.account_id
            GROUP BY a.account_id, a.account_name;
        """)

    # Key Metrics Row
    st.markdown("### Key Metrics")
    metric_cols = st.columns(5)

    total_revenue = float(revenue_df['amount'].sum()) if not revenue_df.empty else 0.0
    total_attributed = float(attribution_df['attributed_amount'].sum()) if not attribution_df.empty else 0.0
    attribution_coverage = (total_attributed / total_revenue * 100) if total_revenue > 0 else 0.0
    total_accounts = len(accounts_df)
    total_partners = len(partners_df)
    total_use_cases = len(use_cases_df)

    with metric_cols[0]:
        st.metric(
            "Total Revenue",
            f"${total_revenue:,.0f}",
            delta=f"{dashboard_days}d period"
        )

    with metric_cols[1]:
        st.metric(
            "Attributed Revenue",
            f"${total_attributed:,.0f}",
            delta=f"{attribution_coverage:.1f}% coverage"
        )

    with metric_cols[2]:
        st.metric(
            "Active Accounts",
            f"{total_accounts}",
            delta=f"{len(ap_df)} with partners"
        )

    with metric_cols[3]:
        st.metric(
            "Partner Count",
            f"{total_partners}",
            delta=f"{len(attribution_df)} active"
        )

    with metric_cols[4]:
        st.metric(
            "Use Cases",
            f"{total_use_cases}",
            delta=f"{len(use_cases_df[use_cases_df['stage'] == 'Live'])} live"
        )

    st.markdown("---")

    # Charts Row 1: Revenue and Attribution
    st.markdown("### Revenue & Attribution Trends")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.plotly_chart(
            create_revenue_over_time_chart(revenue_df),
            use_container_width=True,
            key="revenue_trend"
        )

    with chart_col2:
        st.plotly_chart(
            create_attribution_pie_chart(attribution_df),
            use_container_width=True,
            key="attribution_pie"
        )

    st.markdown("---")

    # Charts Row 2: Partner Performance and Pipeline
    st.markdown("### Partner Performance & Pipeline")
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.plotly_chart(
            create_partner_performance_bar_chart(attribution_df),
            use_container_width=True,
            key="partner_performance"
        )

    with chart_col4:
        st.plotly_chart(
            create_pipeline_funnel_chart(use_cases_df),
            use_container_width=True,
            key="pipeline_funnel"
        )

    st.markdown("---")

    # Charts Row 3: Partner Roles and Attribution Waterfall
    st.markdown("### Partner Insights")
    chart_col5, chart_col6 = st.columns(2)

    with chart_col5:
        st.plotly_chart(
            create_partner_role_distribution(partner_roles_df),
            use_container_width=True,
            key="role_distribution"
        )

    with chart_col6:
        st.plotly_chart(
            create_attribution_waterfall(attribution_df, total_revenue),
            use_container_width=True,
            key="waterfall"
        )

    st.markdown("---")

    # Export Section
    st.markdown("### Export Dashboard Data")
    export_cols = st.columns(4)

    with export_cols[0]:
        if not revenue_df.empty:
            csv_data = export_to_csv(revenue_df, "revenue_data.csv")
            st.download_button(
                "Download Revenue CSV",
                data=csv_data,
                file_name=f"revenue_{start_str}_to_{end_str}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with export_cols[1]:
        if not attribution_df.empty:
            csv_data = export_to_csv(attribution_df, "attribution_data.csv")
            st.download_button(
                "Download Attribution CSV",
                data=csv_data,
                file_name=f"attribution_{start_str}_to_{end_str}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with export_cols[2]:
        if not use_cases_df.empty or not attribution_df.empty:
            excel_data = export_to_excel({
                "Revenue": revenue_df,
                "Attribution": attribution_df,
                "Use Cases": use_cases_df,
                "Partner Roles": partner_roles_df
            })
            st.download_button(
                "Download Excel Report",
                data=excel_data,
                file_name=f"dashboard_report_{start_str}_to_{end_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    with export_cols[3]:
        if not attribution_df.empty:
            pdf_data = create_partner_performance_report(
                attribution_df,
                attribution_df,
                f"{start_str} to {end_str}"
            )
            st.download_button(
                "Download PDF Report",
                data=pdf_data,
                file_name=f"partner_performance_{start_str}_to_{end_str}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    st.markdown("---")

    # Top Performers Table
    st.markdown("### Top Performing Partners")
    if not attribution_df.empty:
        top_partners = attribution_df.head(10).copy()
        top_partners['attributed_amount'] = top_partners['attributed_amount'].apply(lambda x: f"${x:,.2f}")
        top_partners['avg_split_percent'] = top_partners['avg_split_percent'].apply(lambda x: f"{x:.1%}")
        st.dataframe(
            top_partners[['partner_name', 'attributed_amount', 'accounts_influenced', 'avg_split_percent']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No partner attribution data available for the selected period.")

# --- Tab 1: Admin ---
with tabs[1]:
    st.subheader("Settings")
    st.caption("Configure guardrails and reset demo data.")

    settings_left, settings_right = st.columns([2, 1])
    with settings_left:
        enforce_default = should_enforce_split_cap()
        si_mode_default = get_setting("si_auto_split_mode", "live_share")
        si_fixed_default = float(get_setting("si_fixed_percent", "20"))
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
            save_settings = st.form_submit_button("Save settings")
            if save_settings:
                set_setting_bool("enforce_split_cap", enforce_cap)
                set_setting("si_auto_split_mode", si_mode)
                set_setting("si_fixed_percent", str(si_fixed))
                st.success(f"Saved. Enforce split cap = {'ON' if enforce_cap else 'OFF'}.")

    with settings_right:
        st.caption("Admin")
        if st.button("Reset demo data (start fresh)"):
            reset_demo()
            st.success("Reset complete. Refresh the page.")
        if st.button("Recompute ledger (last 30 days)"):
            res = recompute_attribution_ledger(30)
            st.success(f"Ledger recomputed: {res['inserted']} rows, {res['blocked']} blocked, {res['skipped']} skipped.")
        with st.expander("Field palette (use @field in prompts)", expanded=False):
            field_groups = {
                "Use cases": ["use_case_name", "stage", "estimated_value", "target_close_date", "tag_source"],
                "Use case ↔ partner": ["partner_role", "created_at"],
                "Accounts": ["account_id", "account_name"],
                "Partners": ["partner_id", "partner_name"],
                "Revenue events": ["revenue_date", "amount"],
                "Activities": ["activity_type", "activity_date", "notes"],
            }
            for group, fields in field_groups.items():
                st.write(f"- **{group}**: " + ", ".join(f"`@{f}`" for f in fields))

    st.markdown("---")
    st.markdown('<a id="rule-builder"></a>', unsafe_allow_html=True)
    st.subheader("Attribution configuration")
    st.caption("Turn on exactly what you need. No presets—use your own data and rules.")
    use_case_rules_enabled = st.checkbox("Gate use-case links with rules", value=get_setting_bool("enable_use_case_rules", True))
    account_rollup_enabled = st.checkbox("Enable account-level rollup/splits", value=get_setting_bool("enable_account_rollup", True))
    set_setting_bool("enable_use_case_rules", use_case_rules_enabled)
    set_setting_bool("enable_account_rollup", account_rollup_enabled)

    def render_rule_section(title: str, key: str, enabled: bool, applies_to_account: bool):
        st.markdown(f"### {title}")
        if not enabled:
            st.warning("Disabled for current model.")
            return
        st.caption("Rules are created via AI suggestions or natural language below—no manual field-picking needed.")
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
                    })
                st.dataframe(pd.DataFrame(rule_rows), use_container_width=True)
            else:
                st.info("No rules yet. Use AI suggestion or the natural-language converter below to add one.")

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
                    render_apply_summary(apply_rules_auto_assign(account_rollup_enabled))
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
                render_apply_summary(apply_rules_auto_assign(account_rollup_enabled))
            elif not applies_to_account:
                st.caption("Use-case rules gate link creation. Account splits are unaffected.")

    render_rule_section("Use Case Rules (per-link gating)", key="use_case_rules", enabled=use_case_rules_enabled, applies_to_account=False)
    render_rule_section("Account Rules (roll up to account splits)", key="account_rules", enabled=account_rollup_enabled, applies_to_account=True)

    st.markdown("---")
    st.subheader("Natural-language rules → structured")
    nl_text = st.text_area("Describe a rule in plain English", height=100)
    target_rule_set = st.selectbox("Save to", ["use_case_rules", "account_rules"], format_func=lambda k: "Use case rules" if k == "use_case_rules" else "Account rules")
    if st.button("Convert to rule JSON"):
        rule, err = convert_nl_to_rule(nl_text)
        if not validate_rule_obj(rule):
            st.error("Could not parse into a valid rule. Please refine the text.")
        else:
            st.code(json.dumps(rule, indent=2), language="json")
            preview_links = read_sql("""
                SELECT ucp.partner_role, u.stage, u.estimated_value
                FROM use_case_partners ucp
                JOIN use_cases u ON u.use_case_id = ucp.use_case_id;
            """)
            matches = 0
            if not preview_links.empty:
                for _, r in preview_links.iterrows():
                    if evaluate_rules(
                        {"partner_role": r["partner_role"], "stage": r["stage"], "estimated_value": r["estimated_value"]},
                        key=target_rule_set
                    )[0]:
                        matches += 1
                st.info(f"Would match {matches}/{len(preview_links)} existing links.")
            if st.button("Add converted rule"):
                rules = load_rules(target_rule_set)
                rules.append(rule)
                set_setting(target_rule_set, json.dumps(rules, indent=2))
                st.success("Rule added.")
                if target_rule_set == "account_rules":
                    render_apply_summary(apply_rules_auto_assign(account_rollup_enabled))
        if err:
            st.caption(f"LLM note: {err}")

    st.markdown("---")
    st.subheader("Rule impact simulator")
    sim_cols = st.columns([2, 1, 1])
    sim_target = sim_cols[0].selectbox(
        "Which rule set?",
        ["account_rules", "use_case_rules"],
        format_func=lambda k: "Account rules (rollup/ledger)" if k == "account_rules" else "Use case rules (link gating)",
    )
    lookback = sim_cols[1].slider(
        "Lookback (days, for revenue at risk)",
        min_value=7,
        max_value=180,
        value=60,
        help="Used for revenue-at-risk when simulating account rules.",
        disabled=sim_target != "account_rules",
    )
    if sim_cols[2].button("Run simulation"):
        res = simulate_rule_impact(sim_target, days=lookback if sim_target == "account_rules" else 60)
        st.info(
            f"Checked {res['checked']} links. Allowed {res['allowed']}, blocked {res['blocked']}, "
            f"missing context {res['no_context']}."
        )
        metric_cols = st.columns(2)
        if sim_target == "account_rules":
            metric_cols[0].metric("Revenue at risk", f"{res['revenue_at_risk']:,.0f}")
            metric_cols[1].metric("Lookback (days)", res["lookback_days"])
        else:
            metric_cols[0].metric("Est. value blocked", f"{res['estimated_value_blocked']:,.0f}")
            metric_cols[1].metric("Lookback (days)", res["lookback_days"])
        if res.get("details"):
            with st.expander("Blocked details (sample)"):
                st.write("\n".join(res["details"][:15]))

    st.markdown("---")
    st.subheader("AI recommendations (account-level)")
    acct_map_ai = {f"{row['account_name']} ({row['account_id']})": row["account_id"] for _, row in accounts.iterrows()}
    if acct_map_ai:
        acct_choice_ai = st.selectbox("Account for recommendations", list(acct_map_ai.keys()), key="ai_recs_account")
        acct_id_ai = acct_map_ai[acct_choice_ai]
        if st.button("AI recommend attributions for this account"):
            recs, err = generate_ai_recommendations(acct_id_ai)
            run_sql("""
            INSERT INTO ai_recommendations(account_id, created_at, recommendations_json)
            VALUES (?, ?, ?);
            """, (acct_id_ai, datetime.utcnow().isoformat(), json.dumps(recs, indent=2)))
            st.code(json.dumps(recs, indent=2), language="json")
            if err:
                st.caption(f"LLM note: {err}")
        latest_recs = read_sql("""
          SELECT recommendations_json, created_at
          FROM ai_recommendations
          WHERE account_id = ?
          ORDER BY created_at DESC
          LIMIT 1;
        """, (acct_id_ai,))
        if not latest_recs.empty:
            recs = safe_json_loads(latest_recs.loc[0, "recommendations_json"]) or []
            st.caption(f"Latest recommendations at {latest_recs.loc[0, 'created_at']}")
            st.code(json.dumps(recs, indent=2), language="json")
            if st.button("Apply recommendations"):
                stats = apply_recommendations(acct_id_ai, recs)
                st.success(f"Applied: {stats['applied']}, blocked cap: {stats['blocked_cap']}, skipped manual: {stats['skipped_manual']}, invalid: {stats['invalid']}")
                recompute_attribution_ledger(30)
    else:
        st.info("No accounts found.")

    st.markdown("---")
    st.subheader("LLM prompt settings")
    st.caption("Tune the prompts the AI features use. You can reference fields with @stage, @estimated_value, @created_at, etc.")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pr_rule = st.text_area(
            "Rule conversion prompt",
            value=get_setting("prompt_rule_conversion", DEFAULT_SETTINGS["prompt_rule_conversion"]),
            height=120,
        )
        pr_summary = st.text_area(
            "Relationship summary prompt",
            value=get_setting("prompt_relationship_summary", DEFAULT_SETTINGS["prompt_relationship_summary"]),
            height=120,
        )
    with col_p2:
        pr_recs = st.text_area(
            "AI recommendation prompt",
            value=get_setting("prompt_ai_recommendations", DEFAULT_SETTINGS["prompt_ai_recommendations"]),
            height=120,
        )
    if st.button("Save prompts"):
        set_setting("prompt_rule_conversion", pr_rule)
        set_setting("prompt_relationship_summary", pr_summary)
        set_setting("prompt_ai_recommendations", pr_recs)
        st.success("Prompts updated.")

    st.markdown("---")
    st.subheader("Bulk Import / Export")
    st.caption("Import data from CSV or export all data for backup.")

    bulk_tabs = st.tabs(["Import", "Export", "Templates"])

    with bulk_tabs[0]:
        st.markdown("### Bulk Import")
        import_type = st.selectbox(
            "Select data type to import",
            ["accounts", "partners", "use_cases", "use_case_partners"],
            format_func=lambda x: x.replace("_", " ").title()
        )

        uploaded_file = st.file_uploader(
            f"Upload {import_type.replace('_', ' ').title()} CSV",
            type=["csv"],
            key=f"upload_{import_type}"
        )

        if uploaded_file is not None:
            st.info(f"File uploaded: {uploaded_file.name}")

            if st.button(f"Import {import_type.replace('_', ' ').title()}", type="primary"):
                with st.spinner(f"Importing {import_type}..."):
                    csv_content = uploaded_file.read()

                    if import_type == "accounts":
                        success, errors_count, error_msgs = import_accounts_from_csv(csv_content, db)
                    elif import_type == "partners":
                        success, errors_count, error_msgs = import_partners_from_csv(csv_content, db)
                    elif import_type == "use_cases":
                        success, errors_count, error_msgs = import_use_cases_from_csv(csv_content, db)
                    elif import_type == "use_case_partners":
                        success, errors_count, error_msgs = import_use_case_partners_from_csv(csv_content, db)
                    else:
                        success, errors_count, error_msgs = 0, 0, ["Unknown import type"]

                    if success > 0:
                        st.success(f"Successfully imported {success} records!")
                    if errors_count > 0:
                        st.error(f"Failed to import {errors_count} records")
                        with st.expander("View errors"):
                            for msg in error_msgs[:20]:
                                st.text(msg)
                    if success == 0 and errors_count == 0:
                        st.warning("No records were processed")

    with bulk_tabs[1]:
        st.markdown("### Export All Data")
        st.caption("Download a complete backup of all data tables.")

        if st.button("Generate Full Export", type="primary"):
            with st.spinner("Exporting all data..."):
                all_data = export_all_data(db)

                if all_data:
                    excel_data = export_to_excel(all_data)
                    st.download_button(
                        "Download Complete Data Export (Excel)",
                        data=excel_data,
                        file_name=f"attribution_full_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    st.success(f"Export ready! Contains {len(all_data)} tables.")

    with bulk_tabs[2]:
        st.markdown("### CSV Templates")
        st.caption("Download template files for bulk imports.")

        template_cols = st.columns(2)

        with template_cols[0]:
            st.download_button(
                "Accounts Template",
                data=get_import_template('accounts'),
                file_name="accounts_template.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                "Use Cases Template",
                data=get_import_template('use_cases'),
                file_name="use_cases_template.csv",
                mime="text/csv",
                use_container_width=True
            )

        with template_cols[1]:
            st.download_button(
                "Partners Template",
                data=get_import_template('partners'),
                file_name="partners_template.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                "Use Case Partners Template",
                data=get_import_template('use_case_partners'),
                file_name="use_case_partners_template.csv",
                mime="text/csv",
                use_container_width=True
            )

# --- Tab 2: Account Partner 360 ---
with tabs[2]:
    st.subheader("Catalog & links")
    st.caption("Accounts, use cases, and partner links in one place. Imported CRM links will appear here.")
    tag_source_setting = get_setting("use_case_tag_source", "hybrid")
    if tag_source_setting == "crm":
        st.info("Use case tags come from your CRM. Update stage/value in the CRM; this view stays read-only for tags.")
    elif tag_source_setting == "app":
        st.info("Tagging happens here. Use this table to manage stages/values; CRM tags are ignored.")
    else:
        st.info("Hybrid mode: accept CRM-provided tags and allow in-app updates where needed.")
    filter_cols = st.columns(3)
    with filter_cols[0]:
        account_filter = st.selectbox("Filter by account", ["All"] + [f"{row['account_name']} ({row['account_id']})" for _, row in accounts.iterrows()])
    with filter_cols[1]:
        stage_filter = st.selectbox("Filter by stage", ["All", "Discovery", "Evaluation", "Commit", "Live"])
    with filter_cols[2]:
        partner_filter = st.selectbox("Filter by partner", ["All"] + [row["partner_name"] for _, row in read_sql("SELECT partner_name FROM partners ORDER BY partner_name;").iterrows()])

    use_cases = read_sql("""
        SELECT u.use_case_id, u.use_case_name, u.stage, u.estimated_value, u.target_close_date, u.tag_source, a.account_name, a.account_id
        FROM use_cases u
        JOIN accounts a ON a.account_id = u.account_id
        ORDER BY a.account_name, u.use_case_name;
    """)
    st.caption("Auto-assign mode is ON. Splits and roles come from AI/heuristics.")
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
        display_uc = use_cases.rename(columns={"use_case_name": "Use case", "stage": "Stage", "estimated_value": "Est. value", "target_close_date": "Target close", "account_name": "Account", "tag_source": "Tag source"})
        st.dataframe(display_uc, use_container_width=True)

    st.markdown("---")
    st.subheader("Link partner to use case (auto-rollup to AccountPartner)")
    if tag_source_setting == "crm":
        st.warning("Use case attributes (stage/value) are sourced from CRM. Update them there; linking here will still respect CRM tags.")
    elif tag_source_setting == "app":
        st.caption("Use case tags live here. Adjust them in-app as needed.")
    else:
        st.caption("Hybrid tagging: we keep the tag_source on each use case to show whether it came from CRM or in-app edits.")
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
        role_context = st.text_area("Describe partner involvement (optional, used by AI)", height=80)

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

        if st.button("Save use case ↔ partner (auto rollup)"):
            role_choice, role_err = infer_partner_role(
                account_name=uc_row["account_name"],
                use_case_name=uc_row["use_case_name"],
                partner_name=p_choice,
                context=role_context,
            )
            st.info(f"Inferred partner role: {role_choice}")
            if role_err:
                st.caption(f"LLM note: {role_err}")
            # Auto-calculation rule for Implementation partners: allocate split based on use case's share of live or total value.
            if role_choice == "Implementation (SI)":
                auto_split, auto_reason = compute_si_auto_split(uc_value, account_live_total, account_all_total, si_auto_mode)
                if auto_split is not None:
                    source_label = "live total" if account_live_total > 0 else "total estimated (no live use cases)"
                    st.info(
                        f"Auto split for SI: use case value {uc_value:,.0f} / {source_label} {base_total:,.0f} "
                        f"= {auto_split*100:.0f}% ({auto_reason})"
                    )
                    split = auto_split
                else:
                    fallback = float(get_setting("si_fixed_percent", "20")) / 100.0
                    st.warning(f"Auto split not available for this SI rule/data. Applying fallback {fallback*100:.0f}% (change in Admin settings).")
                    split = fallback
            else:
                default_map = {
                    "Influence": inf_default,
                    "Referral": ref_default,
                    "ISV": isv_default,
                }
                split = default_map.get(role_choice, 10) / 100.0
                st.info(f"Auto-assigned {split*100:.0f}% based on role defaults.")
            if get_setting_bool("enable_use_case_rules", True):
                uc_allowed, uc_msg, _, uc_rule_idx, uc_rule_name = evaluate_rules({
                    "partner_role": role_choice,
                    "stage": str(uc_row["stage"]) if pd.notnull(uc_row["stage"]) else None,
                    "estimated_value": uc_value,
                }, key="use_case_rules")
            else:
                uc_allowed, uc_msg, uc_rule_idx, uc_rule_name = True, "Use-case rules disabled", None, None
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
                if get_setting_bool("enable_account_rollup", True):
                    acct_allowed, acct_msg, _, acct_rule_idx, acct_rule_name = evaluate_rules({
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
                    st.success("UseCasePartner saved. Account rollup skipped (rollup disabled).")

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
    st.subheader("Partner leaderboard")
    default_range = (date.today() - timedelta(days=60), date.today())
    date_range = st.date_input("Date range for leaderboard", value=default_range)
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = default_range[0]
        end_date = default_range[1]
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    partner_impact = read_sql("""
      SELECT
        p.partner_name,
        p.partner_id,
        COUNT(DISTINCT ae.account_id) AS accounts_influenced,
        ROUND(SUM(ae.attributed_amount), 2) AS total_attributed_revenue,
        COUNT(DISTINCT ae.revenue_date) AS active_days
      FROM attribution_events ae
      JOIN partners p ON p.partner_id = ae.actor_id
      WHERE ae.revenue_date BETWEEN ? AND ?
      GROUP BY p.partner_name, p.partner_id
      ORDER BY total_attributed_revenue DESC;
    """, (start_str, end_str))
    if partner_filter != "All":
        partner_impact = partner_impact[partner_impact["partner_name"] == partner_filter]
    if partner_impact.empty:
        st.info("No partner impact yet in this window. Link a partner to a use case or create a manual AccountPartner.")
    else:
        st.dataframe(partner_impact, use_container_width=True)
        csv_data = partner_impact.to_csv(index=False)
        st.download_button(
            "Download leaderboard CSV",
            data=csv_data,
            file_name=f"partner_leaderboard_{start_str}_to_{end_str}.csv",
            mime="text/csv",
        )

# --- Tab 3: Account Drilldown ---
with tabs[3]:
    st.subheader("Account drilldown (use cases + revenue)")
    if accounts.empty:
        st.info("No accounts available.")
    else:
        acct_map = {f"{row['account_name']} ({row['account_id']})": row["account_id"] for _, row in accounts.iterrows()}
        acct_choice = st.selectbox("Account", list(acct_map.keys()), key="drilldown_account")
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
            ROUND(SUM(ae.attributed_amount), 2) AS attributed_amount,
            MAX(ae.split_percent) AS split_percent
          FROM attribution_events ae
          JOIN partners p ON p.partner_id = ae.actor_id
          WHERE ae.account_id = ?
            AND ae.revenue_date >= date('now', '-30 day')
          GROUP BY p.partner_name
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

        st.markdown("**Why this credit?**")
        if st.button("Recompute explanations", key=f"recompute_exp_{selected_account_id}"):
            res = recompute_explanations(selected_account_id)
            st.success(f"Wrote {res['written']} explanations for {acct_choice}.")
        exps = read_sql("""
          SELECT partner_id, as_of_date, explanation_json
          FROM attribution_explanations
          WHERE account_id = ?
          ORDER BY created_at DESC;
        """, (selected_account_id,))
        if exps.empty:
            st.caption("No explanations yet. Click recompute to generate.")
        else:
            for _, row in exps.iterrows():
                data = safe_json_loads(row["explanation_json"]) or {}
                partner_name = read_sql("SELECT partner_name FROM partners WHERE partner_id = ?;", (row["partner_id"],))
                partner_label = partner_name.loc[0, "partner_name"] if not partner_name.empty else row["partner_id"]
                with st.expander(f"{partner_label} — as of {row['as_of_date']}"):
                    st.write(f"Source: {data.get('source', 'n/a')} | Split: {data.get('split_percent', 0)*100:.0f}% | Reason: {data.get('split_reason')}")
                    uc_links = data.get("use_case_links", [])
                    if uc_links:
                        st.caption("Use case links")
                        st.table(pd.DataFrame(uc_links))
                    rules = data.get("rule_decisions", {})
                    st.caption(f"Account rules: {rules.get('account', {})}")
                    st.caption(f"Use case rules: {rules.get('use_cases', [])}")

        st.markdown("**Revenue events (30d)**")
        if rev.empty:
            st.info("No revenue events in the last 30 days.")
        else:
            st.dataframe(rev, use_container_width=True)

        # Export Account Drilldown
        st.markdown("---")
        st.markdown("**Export Account Data**")
        export_drilldown_cols = st.columns(3)

        with export_drilldown_cols[0]:
            if not acct_use_cases.empty or not acct_ap.empty:
                excel_data = export_to_excel({
                    "Use Cases": acct_use_cases,
                    "Partners": acct_ap,
                    "Revenue": rev,
                    "Attribution": attr_by_partner
                })
                st.download_button(
                    "Download Account Excel",
                    data=excel_data,
                    file_name=f"account_{selected_account_id}_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        with export_drilldown_cols[1]:
            if not acct_use_cases.empty or not acct_ap.empty:
                pdf_data = create_account_drilldown_report(
                    account_name=acct_choice,
                    use_cases=acct_use_cases,
                    partners=acct_ap,
                    revenue=rev,
                    attribution=attr_by_partner
                )
                st.download_button(
                    "Download Account PDF",
                    data=pdf_data,
                    file_name=f"account_{selected_account_id}_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# --- Tab 4: Relationship Summary (AI) ---
with tabs[4]:
    st.subheader("Relationship Summary (AI)")
    st.caption("Blend accounts, use cases, partners, activities, and recent attribution into a single summary. Works without an API key using a deterministic fallback.")
    acct_map_rel = {f"{row['account_name']} ({row['account_id']})": row["account_id"] for _, row in accounts.iterrows()}
    if not acct_map_rel:
        st.info("No accounts available.")
    else:
        acct_choice_rel = st.selectbox("Account", list(acct_map_rel.keys()), key="rel_summary_account")
        acct_id_rel = acct_map_rel[acct_choice_rel]
        if st.button("Generate summary"):
            summary_text, err = generate_relationship_summary(acct_id_rel)
            run_sql("""
              INSERT INTO ai_summaries(account_id, created_at, summary_text)
              VALUES (?, ?, ?);
            """, (acct_id_rel, datetime.utcnow().isoformat(), summary_text))
            st.success("Summary generated.")
            st.write(summary_text)
            if err:
                st.caption(f"LLM note: {err}")
        latest = read_sql("""
          SELECT summary_text, created_at
          FROM ai_summaries
          WHERE account_id = ?
          ORDER BY created_at DESC
          LIMIT 1;
        """, (acct_id_rel,))
        if not latest.empty:
            st.caption(f"Latest summary ({latest.loc[0, 'created_at']}):")
            st.write(latest.loc[0, "summary_text"])
        st.markdown("**Recent activities**")
        rel_acts = read_sql("""
          SELECT activity_date, activity_type, notes, partner_id
          FROM activities
          WHERE account_id = ?
          ORDER BY activity_date DESC;
        """, (acct_id_rel,))
        if rel_acts.empty:
            st.info("No activities logged.")
        else:
            st.dataframe(rel_acts, use_container_width=True)

# --- Tab 5: Audit Trail ---
with tabs[5]:
    st.subheader("Audit Trail")
    st.caption("Complete history of all changes and decisions in the attribution system")

    # Filters
    filter_row = st.columns([2, 2, 2, 1])
    with filter_row[0]:
        trail_days = st.selectbox(
            "Time Period",
            [7, 14, 30, 60, 90, 180, 365],
            index=2,
            format_func=lambda x: f"Last {x} days",
            key="audit_days"
        )

    with filter_row[1]:
        event_type_filter = st.selectbox(
            "Event Type",
            ["All", "split_change", "partner_link", "use_case_created", "rule_applied", "manual_override"],
            key="event_type_filter"
        )

    with filter_row[2]:
        account_filter_audit = st.selectbox(
            "Account",
            ["All"] + [f"{row['account_name']}" for _, row in accounts.iterrows()],
            key="account_filter_audit"
        )

    with filter_row[3]:
        show_details = st.checkbox("Show Details", value=False, key="audit_details")

    # Calculate date range
    audit_end_date = date.today()
    audit_start_date = audit_end_date - timedelta(days=trail_days)
    audit_start_str = audit_start_date.isoformat()
    audit_end_str = audit_end_date.isoformat()

    # Fetch audit trail
    audit_query = """
        SELECT
            at.timestamp,
            at.event_type,
            at.account_id,
            a.account_name,
            at.partner_id,
            p.partner_name,
            at.old_value,
            at.new_value,
            at.source,
            at.metadata
        FROM audit_trail at
        LEFT JOIN accounts a ON a.account_id = at.account_id
        LEFT JOIN partners p ON p.partner_id = at.partner_id
        WHERE at.timestamp >= ?
    """
    params = [audit_start_str]

    if event_type_filter != "All":
        audit_query += " AND at.event_type = ?"
        params.append(event_type_filter)

    if account_filter_audit != "All":
        audit_query += " AND a.account_name = ?"
        params.append(account_filter_audit)

    audit_query += " ORDER BY at.timestamp DESC LIMIT 1000;"

    audit_trail = read_sql(audit_query, tuple(params))

    # Display metrics
    metrics_audit = st.columns(4)
    with metrics_audit[0]:
        st.metric("Total Events", len(audit_trail))

    if not audit_trail.empty:
        with metrics_audit[1]:
            unique_accounts = audit_trail['account_id'].nunique()
            st.metric("Accounts Affected", unique_accounts)

        with metrics_audit[2]:
            unique_partners = audit_trail['partner_id'].nunique()
            st.metric("Partners Involved", unique_partners)

        with metrics_audit[3]:
            event_types = audit_trail['event_type'].nunique()
            st.metric("Event Types", event_types)

    st.markdown("---")

    # Display audit trail
    if audit_trail.empty:
        st.info("No audit trail events found for the selected filters.")
    else:
        # Format the dataframe for display
        display_audit = audit_trail.copy()

        # Rename columns for better readability
        display_audit['Timestamp'] = pd.to_datetime(display_audit['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        display_audit['Event Type'] = display_audit['event_type']
        display_audit['Account'] = display_audit['account_name'].fillna('N/A')
        display_audit['Partner'] = display_audit['partner_name'].fillna('N/A')

        if show_details:
            display_audit['Old Value'] = display_audit['old_value'].fillna('N/A')
            display_audit['New Value'] = display_audit['new_value'].fillna('N/A')
            display_audit['Source'] = display_audit['source'].fillna('N/A')
            display_audit['Metadata'] = display_audit['metadata'].fillna('N/A')

            st.dataframe(
                display_audit[['Timestamp', 'Event Type', 'Account', 'Partner', 'Old Value', 'New Value', 'Source', 'Metadata']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.dataframe(
                display_audit[['Timestamp', 'Event Type', 'Account', 'Partner']],
                use_container_width=True,
                hide_index=True
            )

    st.markdown("---")

    # Export audit trail
    st.markdown("### Export Audit Trail")
    export_audit_cols = st.columns(3)

    with export_audit_cols[0]:
        if not audit_trail.empty:
            csv_data = export_to_csv(audit_trail, "audit_trail.csv")
            st.download_button(
                "Download Audit Trail CSV",
                data=csv_data,
                file_name=f"audit_trail_{audit_start_str}_to_{audit_end_str}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with export_audit_cols[1]:
        if not audit_trail.empty:
            excel_data = export_to_excel({
                "Audit Trail": audit_trail
            })
            st.download_button(
                "Download Audit Trail Excel",
                data=excel_data,
                file_name=f"audit_trail_{audit_start_str}_to_{audit_end_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    with export_audit_cols[2]:
        if not audit_trail.empty:
            pdf_data = generate_pdf_report(
                title="Audit Trail Report",
                summary_data={
                    "Report Period": f"{audit_start_str} to {audit_end_str}",
                    "Total Events": len(audit_trail),
                    "Accounts Affected": audit_trail['account_id'].nunique(),
                    "Partners Involved": audit_trail['partner_id'].nunique(),
                },
                tables={"Audit Events": audit_trail[['timestamp', 'event_type', 'account_name', 'partner_name', 'source']]}
            )
            st.download_button(
                "Download Audit Trail PDF",
                data=pdf_data,
                file_name=f"audit_trail_{audit_start_str}_to_{audit_end_str}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

