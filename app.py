"""
Attribution MVP - Simplified Partner Attribution System

A clean, intuitive interface for tracking partner attribution.
Designed to be simple for startups, powerful enough for enterprise.

Tab Structure:
1. Dashboard - Overview and metrics
2. Deals - Create deals, link partners, see attribution
3. Partners - Manage your partners
4. Accounts - Manage your customer accounts
5. Settings - Configuration (progressive disclosure)
"""

import json
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

# Import modules
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

# Setup
setup_logging(LOG_LEVEL, LOG_FILE)
db = Database(DB_PATH)
rule_engine = RuleEngine(db)
attribution_engine = AttributionEngine(db, rule_engine)
ai_features = AIFeatures(db)

# Page config
st.set_page_config(
    page_title="Partner Attribution",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Clean, modern styling
st.markdown("""
<style>
    /* Clean background */
    .stApp {
        background: linear-gradient(180deg, #fafbfc 0%, #f0f4f8 100%);
    }

    /* Card styling */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
    }

    /* Tab styling */
    .stTabs [role="tablist"] {
        gap: 8px;
        border-bottom: 2px solid #e5e7eb;
    }
    .stTabs [role="tab"] {
        padding: 0.75rem 1.25rem;
        border-radius: 8px 8px 0 0;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #3b82f6;
        color: white !important;
    }

    /* Form styling */
    .stForm {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
    }

    /* Quick start banner */
    .quick-start {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1f2937;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
db.init_db()
db.seed_data_if_empty()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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

def recompute_attribution_ledger(days: int = 30):
    result = attribution_engine.recompute_attribution_ledger(days)
    return {"inserted": result.inserted, "skipped": result.skipped, "blocked": result.blocked}

# Bootstrap ledger on first load
if "ledger_bootstrap" not in st.session_state:
    recompute_attribution_ledger(30)
    st.session_state["ledger_bootstrap"] = True

# ============================================================================
# LOAD BASE DATA
# ============================================================================

accounts_df = read_sql("SELECT account_id, account_name FROM accounts ORDER BY account_name;")
partners_df = read_sql("SELECT partner_id, partner_name FROM partners ORDER BY partner_name;")
deals_df = read_sql("""
    SELECT u.use_case_id, u.use_case_name, u.stage, u.estimated_value,
           u.target_close_date, u.account_id, a.account_name
    FROM use_cases u
    JOIN accounts a ON a.account_id = u.account_id
    ORDER BY u.use_case_name;
""")

# Check if this is a fresh install (no real data)
is_fresh_install = len(accounts_df) <= 3 and len(partners_df) <= 3

# ============================================================================
# MAIN APP HEADER
# ============================================================================

st.title("Partner Attribution")

# ============================================================================
# TAB STRUCTURE
# ============================================================================

tabs = st.tabs([
    "📊 Dashboard",
    "💼 Deals",
    "🤝 Partners",
    "🏢 Accounts",
    "⚙️ Settings"
])

# ============================================================================
# TAB 1: DASHBOARD
# ============================================================================

with tabs[0]:
    # Quick Start Guide for new users
    if is_fresh_install:
        st.markdown("""
        <div class="quick-start">
            <h3 style="margin:0 0 0.5rem 0; color:white;">Welcome! Let's get you started</h3>
            <p style="margin:0; opacity:0.9;">Follow these steps to set up your attribution tracking:</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Step 1**")
            st.markdown("Add your **Partners** - the companies you work with")
            if st.button("Add Partners →", key="qs_partners"):
                st.info("Go to the Partners tab above")

        with col2:
            st.markdown("**Step 2**")
            st.markdown("Add your **Accounts** - your customers")
            if st.button("Add Accounts →", key="qs_accounts"):
                st.info("Go to the Accounts tab above")

        with col3:
            st.markdown("**Step 3**")
            st.markdown("Create **Deals** - opportunities with your customers")
            if st.button("Create Deals →", key="qs_deals"):
                st.info("Go to the Deals tab above")

        with col4:
            st.markdown("**Step 4**")
            st.markdown("**Link Partners** to deals to track attribution")
            if st.button("Link Partners →", key="qs_link"):
                st.info("Go to the Deals tab above")

        st.markdown("---")

    # Time period selector
    col1, col2 = st.columns([2, 6])
    with col1:
        days = st.selectbox(
            "Time Period",
            [7, 30, 60, 90],
            index=1,
            format_func=lambda x: f"Last {x} days"
        )

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # Fetch metrics
    revenue_df = read_sql("""
        SELECT revenue_date, amount, account_id
        FROM revenue_events
        WHERE revenue_date BETWEEN ? AND ?
        ORDER BY revenue_date;
    """, (start_str, end_str))

    attribution_df = read_sql("""
        SELECT p.partner_name, p.partner_id,
               SUM(ae.attributed_amount) AS attributed_amount,
               COUNT(DISTINCT ae.account_id) AS accounts_influenced
        FROM attribution_events ae
        JOIN partners p ON p.partner_id = ae.actor_id
        WHERE ae.revenue_date BETWEEN ? AND ?
        GROUP BY p.partner_name, p.partner_id
        ORDER BY attributed_amount DESC;
    """, (start_str, end_str))

    # Key Metrics
    st.markdown("### Key Metrics")

    total_revenue = float(revenue_df['amount'].sum()) if not revenue_df.empty else 0.0
    total_attributed = float(attribution_df['attributed_amount'].sum()) if not attribution_df.empty else 0.0
    active_partners = len(attribution_df) if not attribution_df.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"${total_revenue:,.0f}")
    m2.metric("Partner-Attributed", f"${total_attributed:,.0f}")
    m3.metric("Active Deals", len(deals_df))
    m4.metric("Active Partners", active_partners)

    # Charts
    if not revenue_df.empty or not attribution_df.empty:
        st.markdown("---")

        chart1, chart2 = st.columns(2)

        with chart1:
            st.markdown("#### Revenue Trend")
            if not revenue_df.empty:
                st.plotly_chart(
                    create_revenue_over_time_chart(revenue_df),
                    use_container_width=True,
                    key="dash_revenue"
                )
            else:
                st.info("No revenue data yet")

        with chart2:
            st.markdown("#### Attribution by Partner")
            if not attribution_df.empty:
                st.plotly_chart(
                    create_attribution_pie_chart(attribution_df),
                    use_container_width=True,
                    key="dash_attribution"
                )
            else:
                st.info("No attribution data yet")

        # Top Partners Table
        if not attribution_df.empty:
            st.markdown("---")
            st.markdown("#### Top Partners")
            top_partners = attribution_df.head(5).copy()
            top_partners['attributed_amount'] = top_partners['attributed_amount'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(
                top_partners[['partner_name', 'attributed_amount', 'accounts_influenced']].rename(columns={
                    'partner_name': 'Partner',
                    'attributed_amount': 'Attributed Revenue',
                    'accounts_influenced': 'Accounts'
                }),
                use_container_width=True,
                hide_index=True
            )

    # Export
    with st.expander("Export Dashboard Data"):
        exp1, exp2 = st.columns(2)
        with exp1:
            if not attribution_df.empty:
                csv_data = export_to_csv(attribution_df, "attribution.csv")
                st.download_button(
                    "Download Attribution CSV",
                    data=csv_data,
                    file_name=f"attribution_{start_str}_{end_str}.csv",
                    mime="text/csv"
                )
        with exp2:
            if not attribution_df.empty:
                excel_data = export_to_excel({
                    "Revenue": revenue_df,
                    "Attribution": attribution_df
                })
                st.download_button(
                    "Download Excel Report",
                    data=excel_data,
                    file_name=f"report_{start_str}_{end_str}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


# ============================================================================
# TAB 2: DEALS
# ============================================================================

with tabs[1]:
    st.markdown("### Deals & Attribution")
    st.caption("Create deals, link partners, and track who gets credit")

    # Refresh data
    deals_df = read_sql("""
        SELECT u.use_case_id, u.use_case_name, u.stage, u.estimated_value,
               u.target_close_date, u.account_id, a.account_name
        FROM use_cases u
        JOIN accounts a ON a.account_id = u.account_id
        ORDER BY a.account_name, u.use_case_name;
    """)

    # Two column layout: Create Deal | Link Partner
    create_col, link_col = st.columns(2)

    # --- Create Deal ---
    with create_col:
        st.markdown("#### Create New Deal")

        if accounts_df.empty:
            st.warning("Add an account first before creating deals")
        else:
            with st.form("create_deal", clear_on_submit=True):
                account_options = {row['account_name']: row['account_id'] for _, row in accounts_df.iterrows()}
                selected_account = st.selectbox("Account", list(account_options.keys()))

                deal_name = st.text_input("Deal Name", placeholder="e.g., Q1 Expansion")

                col1, col2 = st.columns(2)
                with col1:
                    stage = st.selectbox("Stage", ["Discovery", "Evaluation", "Commit", "Live"])
                with col2:
                    value = st.number_input("Estimated Value ($)", min_value=0, value=50000, step=5000)

                close_date = st.date_input("Target Close Date", value=date.today() + timedelta(days=90))

                if st.form_submit_button("Create Deal", type="primary"):
                    if deal_name.strip():
                        deal_id = f"UC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        run_sql("""
                            INSERT INTO use_cases (use_case_id, account_id, use_case_name, stage,
                                                   estimated_value, target_close_date, tag_source)
                            VALUES (?, ?, ?, ?, ?, ?, 'app');
                        """, (deal_id, account_options[selected_account], deal_name.strip(),
                              stage, value, close_date.isoformat()))
                        st.success(f"Deal '{deal_name}' created!")
                        st.rerun()
                    else:
                        st.error("Please enter a deal name")

    # --- Link Partner to Deal ---
    with link_col:
        st.markdown("#### Link Partner to Deal")

        if deals_df.empty or partners_df.empty:
            st.warning("You need at least one deal and one partner")
        else:
            with st.form("link_partner", clear_on_submit=True):
                # Deal selector
                deal_options = {
                    f"{row['account_name']} - {row['use_case_name']} (${row['estimated_value']:,.0f})": row['use_case_id']
                    for _, row in deals_df.iterrows()
                }
                selected_deal = st.selectbox("Select Deal", list(deal_options.keys()))

                # Partner selector
                partner_options = {row['partner_name']: row['partner_id'] for _, row in partners_df.iterrows()}
                selected_partner = st.selectbox("Select Partner", list(partner_options.keys()))

                # Role selector
                role = st.selectbox(
                    "Partner Role",
                    PARTNER_ROLES,
                    help="Implementation (SI) = delivery partner, Influence = advisor, Referral = sourced the deal, ISV = software vendor"
                )

                # Split percentage
                default_splits = {
                    "Implementation (SI)": 20,
                    "Influence": 10,
                    "Referral": 15,
                    "ISV": 10
                }
                split = st.slider("Attribution Split %", 0, 100, default_splits.get(role, 10))

                if st.form_submit_button("Link Partner", type="primary"):
                    deal_id = deal_options[selected_deal]
                    partner_id = partner_options[selected_partner]

                    # Get deal info for attribution
                    deal_row = deals_df[deals_df['use_case_id'] == deal_id].iloc[0]

                    # Save use_case_partner link
                    run_sql("""
                        INSERT INTO use_case_partners (use_case_id, partner_id, partner_role, created_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(use_case_id, partner_id) DO UPDATE SET partner_role = excluded.partner_role;
                    """, (deal_id, partner_id, role, date.today().isoformat()))

                    # Auto-rollup to account_partners if enabled
                    if get_setting_bool("enable_account_rollup", True):
                        result = attribution_engine.upsert_account_partner_from_use_case_partner(
                            use_case_id=deal_id,
                            partner_id=partner_id,
                            partner_role=role,
                            split_percent=split / 100.0
                        )

                        if result.status == "blocked_split_cap":
                            st.warning(f"Link saved, but account split blocked (would exceed 100%)")
                        elif result.status == "skipped_manual":
                            st.info("Link saved. Account split unchanged (set manually)")
                        else:
                            st.success(f"Partner linked with {split}% attribution!")
                    else:
                        st.success("Partner linked to deal!")

                    st.rerun()

    st.markdown("---")

    # --- Deals List with Attribution ---
    st.markdown("#### All Deals")

    # Filters
    filter1, filter2, filter3 = st.columns(3)
    with filter1:
        stage_filter = st.selectbox("Filter by Stage", ["All", "Discovery", "Evaluation", "Commit", "Live"])
    with filter2:
        account_filter = st.selectbox(
            "Filter by Account",
            ["All"] + list(accounts_df['account_name'])
        )
    with filter3:
        partner_filter = st.selectbox(
            "Filter by Partner",
            ["All"] + list(partners_df['partner_name'])
        )

    # Get deals with partner info
    deals_with_partners = read_sql("""
        SELECT
            u.use_case_id,
            u.use_case_name AS "Deal",
            a.account_name AS "Account",
            u.stage AS "Stage",
            u.estimated_value AS "Value",
            GROUP_CONCAT(p.partner_name || ' (' || ucp.partner_role || ')', ', ') AS "Partners"
        FROM use_cases u
        JOIN accounts a ON a.account_id = u.account_id
        LEFT JOIN use_case_partners ucp ON ucp.use_case_id = u.use_case_id
        LEFT JOIN partners p ON p.partner_id = ucp.partner_id
        GROUP BY u.use_case_id, u.use_case_name, a.account_name, u.stage, u.estimated_value
        ORDER BY a.account_name, u.use_case_name;
    """)

    # Apply filters
    if stage_filter != "All":
        deals_with_partners = deals_with_partners[deals_with_partners['Stage'] == stage_filter]
    if account_filter != "All":
        deals_with_partners = deals_with_partners[deals_with_partners['Account'] == account_filter]
    if partner_filter != "All":
        deals_with_partners = deals_with_partners[
            deals_with_partners['Partners'].str.contains(partner_filter, na=False)
        ]

    if deals_with_partners.empty:
        st.info("No deals found. Create one above!")
    else:
        # Format for display
        display_df = deals_with_partners.copy()
        display_df['Value'] = display_df['Value'].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "-")
        display_df['Partners'] = display_df['Partners'].fillna("No partners linked")

        st.dataframe(
            display_df[['Deal', 'Account', 'Stage', 'Value', 'Partners']],
            use_container_width=True,
            hide_index=True
        )

    # --- Deal Details Expander ---
    if not deals_with_partners.empty:
        with st.expander("View Deal Details & Attribution"):
            deal_select = st.selectbox(
                "Select a deal to view details",
                [f"{row['Account']} - {row['Deal']}" for _, row in deals_with_partners.iterrows()]
            )

            selected_idx = [f"{row['Account']} - {row['Deal']}" for _, row in deals_with_partners.iterrows()].index(deal_select)
            selected_deal_id = deals_with_partners.iloc[selected_idx]['use_case_id']

            # Get partners for this deal
            deal_partners = read_sql("""
                SELECT p.partner_name, ucp.partner_role,
                       ap.split_percent, ap.source
                FROM use_case_partners ucp
                JOIN partners p ON p.partner_id = ucp.partner_id
                LEFT JOIN account_partners ap ON ap.partner_id = ucp.partner_id
                    AND ap.account_id = (SELECT account_id FROM use_cases WHERE use_case_id = ?)
                WHERE ucp.use_case_id = ?;
            """, (selected_deal_id, selected_deal_id))

            if deal_partners.empty:
                st.info("No partners linked to this deal")
            else:
                deal_partners['split_percent'] = deal_partners['split_percent'].apply(
                    lambda x: f"{x*100:.0f}%" if pd.notnull(x) else "-"
                )
                st.dataframe(
                    deal_partners.rename(columns={
                        'partner_name': 'Partner',
                        'partner_role': 'Role',
                        'split_percent': 'Account Split',
                        'source': 'Source'
                    }),
                    use_container_width=True,
                    hide_index=True
                )


# ============================================================================
# TAB 3: PARTNERS
# ============================================================================

with tabs[2]:
    st.markdown("### Partners")
    st.caption("Manage the partners you work with")

    # Add Partner form
    with st.expander("Add New Partner", expanded=len(partners_df) < 3):
        with st.form("add_partner", clear_on_submit=True):
            partner_name = st.text_input("Partner Name", placeholder="e.g., Acme Consulting")

            if st.form_submit_button("Add Partner", type="primary"):
                if partner_name.strip():
                    partner_id = f"P-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    run_sql("""
                        INSERT INTO partners (partner_id, partner_name)
                        VALUES (?, ?)
                        ON CONFLICT(partner_id) DO NOTHING;
                    """, (partner_id, partner_name.strip()))
                    st.success(f"Partner '{partner_name}' added!")
                    st.rerun()
                else:
                    st.error("Please enter a partner name")

    st.markdown("---")

    # Partners list with performance
    st.markdown("#### Partner Performance")

    # Time period for metrics
    perf_days = st.selectbox(
        "Performance Period",
        [30, 60, 90],
        format_func=lambda x: f"Last {x} days",
        key="partner_perf_days"
    )

    perf_start = (date.today() - timedelta(days=perf_days)).isoformat()
    perf_end = date.today().isoformat()

    partner_performance = read_sql("""
        SELECT
            p.partner_id,
            p.partner_name AS "Partner",
            COUNT(DISTINCT ucp.use_case_id) AS "Deals Linked",
            COUNT(DISTINCT ap.account_id) AS "Accounts",
            COALESCE(SUM(ae.attributed_amount), 0) AS "Attributed Revenue"
        FROM partners p
        LEFT JOIN use_case_partners ucp ON ucp.partner_id = p.partner_id
        LEFT JOIN account_partners ap ON ap.partner_id = p.partner_id
        LEFT JOIN attribution_events ae ON ae.actor_id = p.partner_id
            AND ae.revenue_date BETWEEN ? AND ?
        GROUP BY p.partner_id, p.partner_name
        ORDER BY "Attributed Revenue" DESC;
    """, (perf_start, perf_end))

    if partner_performance.empty:
        st.info("No partners yet. Add one above!")
    else:
        display_perf = partner_performance.copy()
        display_perf['Attributed Revenue'] = display_perf['Attributed Revenue'].apply(
            lambda x: f"${x:,.0f}"
        )

        st.dataframe(
            display_perf[['Partner', 'Deals Linked', 'Accounts', 'Attributed Revenue']],
            use_container_width=True,
            hide_index=True
        )

        # Partner detail view
        with st.expander("Partner Details"):
            selected_partner = st.selectbox(
                "Select Partner",
                partner_performance['Partner'].tolist(),
                key="partner_detail_select"
            )

            partner_id = partner_performance[
                partner_performance['Partner'] == selected_partner
            ]['partner_id'].iloc[0]

            # Get deals for this partner
            partner_deals = read_sql("""
                SELECT
                    u.use_case_name AS "Deal",
                    a.account_name AS "Account",
                    u.stage AS "Stage",
                    ucp.partner_role AS "Role"
                FROM use_case_partners ucp
                JOIN use_cases u ON u.use_case_id = ucp.use_case_id
                JOIN accounts a ON a.account_id = u.account_id
                WHERE ucp.partner_id = ?
                ORDER BY a.account_name;
            """, (partner_id,))

            if partner_deals.empty:
                st.info("No deals linked to this partner")
            else:
                st.dataframe(partner_deals, use_container_width=True, hide_index=True)

    # Export
    with st.expander("Export Partner Data"):
        if not partner_performance.empty:
            csv_data = export_to_csv(partner_performance, "partners.csv")
            st.download_button(
                "Download Partners CSV",
                data=csv_data,
                file_name="partners.csv",
                mime="text/csv"
            )


# ============================================================================
# TAB 4: ACCOUNTS
# ============================================================================

with tabs[3]:
    st.markdown("### Accounts")
    st.caption("Manage your customer accounts")

    # Add Account form
    with st.expander("Add New Account", expanded=len(accounts_df) < 3):
        with st.form("add_account", clear_on_submit=True):
            account_name = st.text_input("Account Name", placeholder="e.g., TechCorp Inc")

            if st.form_submit_button("Add Account", type="primary"):
                if account_name.strip():
                    account_id = f"A-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    run_sql("""
                        INSERT INTO accounts (account_id, account_name)
                        VALUES (?, ?)
                        ON CONFLICT(account_id) DO NOTHING;
                    """, (account_id, account_name.strip()))
                    st.success(f"Account '{account_name}' added!")
                    st.rerun()
                else:
                    st.error("Please enter an account name")

    st.markdown("---")

    # Accounts list with metrics
    st.markdown("#### Account Overview")

    account_overview = read_sql("""
        SELECT
            a.account_id,
            a.account_name AS "Account",
            COUNT(DISTINCT u.use_case_id) AS "Deals",
            COUNT(DISTINCT ap.partner_id) AS "Partners",
            COALESCE(SUM(CASE WHEN u.stage = 'Live' THEN u.estimated_value ELSE 0 END), 0) AS "Live Value",
            COALESCE(SUM(u.estimated_value), 0) AS "Total Pipeline"
        FROM accounts a
        LEFT JOIN use_cases u ON u.account_id = a.account_id
        LEFT JOIN account_partners ap ON ap.account_id = a.account_id
        GROUP BY a.account_id, a.account_name
        ORDER BY "Total Pipeline" DESC;
    """)

    if account_overview.empty:
        st.info("No accounts yet. Add one above!")
    else:
        display_acc = account_overview.copy()
        display_acc['Live Value'] = display_acc['Live Value'].apply(lambda x: f"${x:,.0f}")
        display_acc['Total Pipeline'] = display_acc['Total Pipeline'].apply(lambda x: f"${x:,.0f}")

        st.dataframe(
            display_acc[['Account', 'Deals', 'Partners', 'Live Value', 'Total Pipeline']],
            use_container_width=True,
            hide_index=True
        )

        # Account detail view
        with st.expander("Account Details"):
            selected_account = st.selectbox(
                "Select Account",
                account_overview['Account'].tolist(),
                key="account_detail_select"
            )

            account_id = account_overview[
                account_overview['Account'] == selected_account
            ]['account_id'].iloc[0]

            # Get deals for this account
            account_deals = read_sql("""
                SELECT
                    u.use_case_name AS "Deal",
                    u.stage AS "Stage",
                    u.estimated_value AS "Value"
                FROM use_cases u
                WHERE u.account_id = ?
                ORDER BY u.estimated_value DESC;
            """, (account_id,))

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Deals**")
                if account_deals.empty:
                    st.info("No deals")
                else:
                    account_deals['Value'] = account_deals['Value'].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "-")
                    st.dataframe(account_deals, use_container_width=True, hide_index=True)

            with col2:
                st.markdown("**Partners**")
                account_partners = read_sql("""
                    SELECT
                        p.partner_name AS "Partner",
                        ap.split_percent AS "Split",
                        ap.source AS "Source"
                    FROM account_partners ap
                    JOIN partners p ON p.partner_id = ap.partner_id
                    WHERE ap.account_id = ?
                    ORDER BY ap.split_percent DESC;
                """, (account_id,))

                if account_partners.empty:
                    st.info("No partners linked")
                else:
                    account_partners['Split'] = account_partners['Split'].apply(
                        lambda x: f"{x*100:.0f}%" if pd.notnull(x) else "-"
                    )
                    st.dataframe(account_partners, use_container_width=True, hide_index=True)

            # Revenue for this account
            st.markdown("**Recent Revenue (30d)**")
            account_revenue = read_sql("""
                SELECT revenue_date AS "Date", amount AS "Amount"
                FROM revenue_events
                WHERE account_id = ?
                AND revenue_date >= date('now', '-30 day')
                ORDER BY revenue_date DESC
                LIMIT 10;
            """, (account_id,))

            if account_revenue.empty:
                st.info("No recent revenue")
            else:
                account_revenue['Amount'] = account_revenue['Amount'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(account_revenue, use_container_width=True, hide_index=True)


# ============================================================================
# TAB 5: SETTINGS
# ============================================================================

with tabs[4]:
    st.markdown("### Settings")
    st.caption("Configure your attribution system")

    # Basic Settings (always visible)
    st.markdown("#### Basic Settings")

    basic1, basic2 = st.columns(2)

    with basic1:
        enforce_cap = st.checkbox(
            "Enforce 100% split cap",
            value=get_setting_bool("enforce_split_cap", True),
            help="Prevent total account attribution from exceeding 100%"
        )
        if enforce_cap != get_setting_bool("enforce_split_cap", True):
            set_setting_bool("enforce_split_cap", enforce_cap)
            st.success("Setting saved")

    with basic2:
        enable_rollup = st.checkbox(
            "Auto-rollup to account splits",
            value=get_setting_bool("enable_account_rollup", True),
            help="Automatically update account-level splits when linking partners to deals"
        )
        if enable_rollup != get_setting_bool("enable_account_rollup", True):
            set_setting_bool("enable_account_rollup", enable_rollup)
            st.success("Setting saved")

    st.markdown("---")

    # Default Split Percentages
    st.markdown("#### Default Attribution Splits")
    st.caption("Set default split percentages by partner role")

    split_cols = st.columns(4)

    with split_cols[0]:
        si_split = st.number_input(
            "Implementation (SI)",
            min_value=0, max_value=100,
            value=int(get_setting("si_fixed_percent", "20")),
            key="si_split_setting"
        )
        if str(si_split) != get_setting("si_fixed_percent", "20"):
            set_setting("si_fixed_percent", str(si_split))

    with split_cols[1]:
        inf_split = st.number_input(
            "Influence",
            min_value=0, max_value=100,
            value=int(get_setting("default_split_influence", "10")),
            key="inf_split_setting"
        )
        if str(inf_split) != get_setting("default_split_influence", "10"):
            set_setting("default_split_influence", str(inf_split))

    with split_cols[2]:
        ref_split = st.number_input(
            "Referral",
            min_value=0, max_value=100,
            value=int(get_setting("default_split_referral", "15")),
            key="ref_split_setting"
        )
        if str(ref_split) != get_setting("default_split_referral", "15"):
            set_setting("default_split_referral", str(ref_split))

    with split_cols[3]:
        isv_split = st.number_input(
            "ISV",
            min_value=0, max_value=100,
            value=int(get_setting("default_split_isv", "10")),
            key="isv_split_setting"
        )
        if str(isv_split) != get_setting("default_split_isv", "10"):
            set_setting("default_split_isv", str(isv_split))

    st.markdown("---")

    # Advanced Settings (collapsed by default)
    with st.expander("Advanced Settings", expanded=False):
        st.markdown("#### SI Auto-Split Mode")
        si_mode = st.selectbox(
            "How to calculate Implementation (SI) partner splits",
            ["fixed_percent", "live_share", "manual_only"],
            index=["fixed_percent", "live_share", "manual_only"].index(
                get_setting("si_auto_split_mode", "fixed_percent")
            ),
            format_func=lambda x: {
                "fixed_percent": "Fixed Percentage (use default above)",
                "live_share": "Live Share (based on deal value vs account total)",
                "manual_only": "Manual Only (always set manually)"
            }[x]
        )
        if si_mode != get_setting("si_auto_split_mode", "fixed_percent"):
            set_setting("si_auto_split_mode", si_mode)
            st.success("SI mode updated")

        st.markdown("---")

        st.markdown("#### Use Case Rules")
        enable_uc_rules = st.checkbox(
            "Enable deal-level rules",
            value=get_setting_bool("enable_use_case_rules", False),
            help="Gate partner linking based on deal attributes"
        )
        if enable_uc_rules != get_setting_bool("enable_use_case_rules", False):
            set_setting_bool("enable_use_case_rules", enable_uc_rules)

    st.markdown("---")

    # Data Management
    with st.expander("Data Management", expanded=False):
        st.markdown("#### Bulk Import")

        import_type = st.selectbox(
            "Data Type",
            ["accounts", "partners", "use_cases"],
            format_func=lambda x: x.replace("_", " ").title()
        )

        uploaded = st.file_uploader(f"Upload {import_type} CSV", type=['csv'], key="bulk_import")

        if uploaded and st.button("Import Data"):
            csv_content = uploaded.read()
            if import_type == "accounts":
                success, errors, msgs = import_accounts_from_csv(csv_content, db)
            elif import_type == "partners":
                success, errors, msgs = import_partners_from_csv(csv_content, db)
            elif import_type == "use_cases":
                success, errors, msgs = import_use_cases_from_csv(csv_content, db)
            else:
                success, errors, msgs = 0, 0, []

            if success > 0:
                st.success(f"Imported {success} records")
            if errors > 0:
                st.error(f"Failed: {errors} records")

        st.markdown("---")

        st.markdown("#### Export All Data")
        if st.button("Generate Full Export"):
            all_data = export_all_data(db)
            if all_data:
                excel_data = export_to_excel(all_data)
                st.download_button(
                    "Download Complete Export",
                    data=excel_data,
                    file_name=f"full_export_{date.today().isoformat()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        st.markdown("---")

        st.markdown("#### Templates")
        t1, t2, t3 = st.columns(3)
        with t1:
            st.download_button(
                "Accounts Template",
                data=get_import_template('accounts'),
                file_name="accounts_template.csv",
                mime="text/csv"
            )
        with t2:
            st.download_button(
                "Partners Template",
                data=get_import_template('partners'),
                file_name="partners_template.csv",
                mime="text/csv"
            )
        with t3:
            st.download_button(
                "Deals Template",
                data=get_import_template('use_cases'),
                file_name="deals_template.csv",
                mime="text/csv"
            )

    # System Actions
    with st.expander("System Actions", expanded=False):
        st.markdown("#### Recompute Attribution")
        if st.button("Recalculate Attribution Ledger (30 days)"):
            res = recompute_attribution_ledger(30)
            st.success(f"Processed: {res['inserted']} entries")

        st.markdown("---")

        st.markdown("#### Reset Data")
        st.warning("This will delete all data and reset to demo state")
        if st.button("Reset to Demo Data", type="secondary"):
            db.reset_demo()
            st.success("Reset complete. Refresh the page.")

    # Audit Trail
    with st.expander("Audit Trail", expanded=False):
        st.markdown("#### Recent Changes")

        audit_days = st.selectbox(
            "Period",
            [7, 30, 60],
            format_func=lambda x: f"Last {x} days",
            key="audit_period"
        )

        audit_start = (date.today() - timedelta(days=audit_days)).isoformat()

        audit_trail = read_sql("""
            SELECT
                at.timestamp AS "Time",
                at.event_type AS "Event",
                a.account_name AS "Account",
                p.partner_name AS "Partner",
                at.old_value AS "Old",
                at.new_value AS "New"
            FROM audit_trail at
            LEFT JOIN accounts a ON a.account_id = at.account_id
            LEFT JOIN partners p ON p.partner_id = at.partner_id
            WHERE at.timestamp >= ?
            ORDER BY at.timestamp DESC
            LIMIT 100;
        """, (audit_start,))

        if audit_trail.empty:
            st.info("No changes in this period")
        else:
            st.dataframe(audit_trail, use_container_width=True, hide_index=True)

            csv_data = export_to_csv(audit_trail, "audit.csv")
            st.download_button(
                "Download Audit Trail",
                data=csv_data,
                file_name=f"audit_{audit_start}.csv",
                mime="text/csv"
            )
