"""
Attribution MVP - Universal Architecture
=========================================

Rebuilt with universal 4-table schema:
- AttributionTarget (what gets credit)
- PartnerTouchpoint (evidence of partner involvement)
- AttributionRule (config-driven calculation logic)
- AttributionLedger (immutable results with audit trails)

Key Features:
- CSV upload with auto schema detection
- Template selection (1-click attribution models)
- Natural language rule creation
- Config-driven attribution (no hardcoded logic)
- **PRESERVED DASHBOARD** (identical to original)
"""

import streamlit as st
import pandas as pd
import json
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import warnings

# Suppress deprecation warnings
warnings.filterwarnings('ignore', message='.*Plotly configuration.*')
warnings.filterwarnings('ignore', message='.*label.*got an empty value.*')

# New universal architecture imports
from models_new import (
    AttributionTarget, PartnerTouchpoint, AttributionRule, LedgerEntry,
    TargetType, TouchpointType, AttributionModel, SplitConstraint,
    DEFAULT_PARTNER_ROLES, SCHEMA_VERSION,
    # NEW: Universal attribution types
    ActorType, RevenueType, Touchpoint
)
from attribution_engine import AttributionEngine, select_rule_for_target
from data_ingestion import ingest_csv, generate_csv_template, SchemaDetector
from nl_rule_parser import parse_nl_to_rule, get_example_prompts
from templates import list_templates, get_template, recommend_template
from demo_data import generate_complete_demo_data, get_demo_data_summary, DEMO_PARTNER_NAMES

# Preserve original dashboard visualizations
from dashboards import (
    create_revenue_over_time_chart,
    create_partner_performance_bar_chart,
    create_attribution_pie_chart,
    create_deal_value_distribution,
    create_partner_role_distribution,
    create_attribution_waterfall,
    # Revenue Relationships dashboard
    create_revenue_by_actor_type_chart,
    create_revenue_by_type_chart,
    create_actor_contribution_trend,
    create_revenue_relationship_sankey,
    create_top_contributors_table,
    create_revenue_type_comparison_chart,
    # Dreamdata-style components
    create_journey_timeline,
    create_attribution_model_comparison,
    calculate_kpi_metrics,
    create_deal_journey_detail,
    render_kpi_cards
)
from exports import export_to_csv, export_to_excel, generate_pdf_report, generate_partner_statement_pdf, generate_bulk_partner_statements
from pdf_executive_report import generate_executive_report

# Partner management dashboards
from partner_analytics import (
    calculate_health_score, calculate_period_comparison, detect_alerts,
    calculate_win_rate, calculate_deal_velocity, generate_partner_insights,
    get_top_movers
)
from dashboards_partner import (
    create_health_gauge, create_health_score_breakdown,
    create_period_comparison_chart, create_top_movers_chart,
    create_partner_revenue_trend, create_partner_activity_trend
)
from utils_partner import (
    format_days_ago, format_growth_percentage, format_currency_compact,
    get_trend_indicator, classify_health_grade, get_health_emoji,
    get_grade_description, format_percentage
)

# Database persistence
from db_universal import Database
from session_manager import SessionManager

# Authentication
from login_page import (
    check_authentication,
    render_login_page,
    render_user_info_sidebar,
    get_current_organization_id,
    can_user_approve_touchpoints
)

# Approval workflow
from approval_workflow import (
    render_approval_queue,
    render_approval_history,
    render_approval_stats
)

# Period management
from period_management import render_period_management

# ============================================================================
# Authentication Check
# ============================================================================

DB_PATH = "attribution.db"

# Check if user is authenticated
if not check_authentication(DB_PATH):
    render_login_page(DB_PATH)
    st.stop()

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Attribution MVP - Universal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-aware styling for light and dark modes
st.markdown("""
<style>
/* Light theme (default) */
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
    background: rgba(242, 244, 248, 0.8);
    padding: 0.35rem 0.75rem;
    border: 1px solid rgba(224, 230, 239, 0.8);
}
.stTabs [aria-selected="true"] {
    background: rgba(215, 227, 255, 0.9);
    border-color: rgba(182, 204, 255, 0.9);
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

/* Dark theme overrides */
@media (prefers-color-scheme: dark) {
    body {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%);
    }

    .stTabs [role="tab"] {
        background: rgba(45, 55, 72, 0.8);
        border: 1px solid rgba(74, 85, 104, 0.8);
        color: rgba(255, 255, 255, 0.9) !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(66, 153, 225, 0.3);
        border-color: rgba(66, 153, 225, 0.6);
        color: #90cdf4 !important;
        font-weight: 600;
    }

    .metric-card {
        background: rgba(45, 55, 72, 0.6);
        border: 1px solid rgba(74, 85, 104, 0.6);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }

    /* Better button visibility in dark mode */
    .stButton > button {
        background-color: rgba(66, 153, 225, 0.15) !important;
        border: 2px solid rgba(66, 153, 225, 0.4) !important;
        color: rgba(255, 255, 255, 0.95) !important;
    }

    .stButton > button:hover {
        background-color: rgba(66, 153, 225, 0.25) !important;
        border-color: rgba(66, 153, 225, 0.7) !important;
        box-shadow: 0 0 12px rgba(66, 153, 225, 0.3) !important;
    }

    .stButton > button[kind="primary"] {
        background-color: rgba(66, 153, 225, 0.4) !important;
        border-color: rgba(66, 153, 225, 0.8) !important;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: rgba(66, 153, 225, 0.5) !important;
        box-shadow: 0 0 16px rgba(66, 153, 225, 0.5) !important;
    }
}

/* Streamlit's dark theme class override */
[data-testid="stAppViewContainer"][data-theme="dark"] .stButton > button {
    background-color: rgba(66, 153, 225, 0.15) !important;
    border: 2px solid rgba(66, 153, 225, 0.4) !important;
    color: rgba(255, 255, 255, 0.95) !important;
}

[data-testid="stAppViewContainer"][data-theme="dark"] .stButton > button:hover {
    background-color: rgba(66, 153, 225, 0.25) !important;
    border-color: rgba(66, 153, 225, 0.7) !important;
    box-shadow: 0 0 12px rgba(66, 153, 225, 0.3) !important;
}

[data-testid="stAppViewContainer"][data-theme="dark"] .stButton > button[kind="primary"] {
    background-color: rgba(66, 153, 225, 0.4) !important;
    border-color: rgba(66, 153, 225, 0.8) !important;
}

[data-testid="stAppViewContainer"][data-theme="dark"] .stButton > button[kind="primary"]:hover {
    background-color: rgba(66, 153, 225, 0.5) !important;
    box-shadow: 0 0 16px rgba(66, 153, 225, 0.5) !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Database & Session Management
# ============================================================================

# Initialize database (DB_PATH defined in authentication section above)
if "db_initialized" not in st.session_state:
    db = Database(DB_PATH)
    db.init_db()
    st.session_state.db_initialized = True

    # Create default organization and admin user if they don't exist
    from auth import create_default_organization_and_admin
    create_default_organization_and_admin(DB_PATH)

# Initialize session manager
if "session_manager" not in st.session_state:
    st.session_state.session_manager = SessionManager(DB_PATH)
    st.session_state.session_manager.initialize_session_state()

# Ensure we have some demo partners for backwards compatibility
if not st.session_state.partners:
    demo_partners = {
        "P001": "CloudConsult Partners",
        "P002": "DataWorks SI",
        "P003": "AnalyticsPro",
        "P004": "TechAlliance Inc",
        "P005": "InnovateCo",
        "P006": "SystemsPartner LLC",
        "P007": "GlobalTech Solutions",
        "P008": "EnterprisePartners"
    }
    for pid, pname in demo_partners.items():
        st.session_state.session_manager.add_partner(pid, pname)

# Global filters state (UI only, not persisted)
if "global_filters" not in st.session_state:
    st.session_state.global_filters = {
        "date_range": (date.today() - timedelta(days=90), date.today()),
        "selected_partners": [],
        "deal_stage": "All",
        "min_deal_size": 0
    }

# Metric visibility toggles (UI only, not persisted)
if "visible_metrics" not in st.session_state:
    st.session_state.visible_metrics = {
        "revenue": True,
        "deal_count": True,
        "active_partners": True,
        "avg_deal_size": True,
        "win_rate": False,
        "deal_velocity": False
    }


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_attribution_for_all_targets():
    """
    Run attribution calculations for all targets using all active rules.
    Populates the ledger and persists to database.
    """
    engine = AttributionEngine()
    session_mgr = st.session_state.session_manager

    # Use session manager's recalculation which persists to database
    entries_created = session_mgr.recalculate_attribution(engine)

    return entries_created


def get_ledger_as_dataframe() -> pd.DataFrame:
    """
    Convert ledger to DataFrame for dashboard queries.

    Mimics the structure of the original attribution_events table.
    """
    if not st.session_state.ledger:
        return pd.DataFrame(columns=[
            "partner_id", "partner_name", "attributed_amount",
            "split_percent", "revenue_date", "account_id"
        ])

    rows = []
    for entry in st.session_state.ledger:
        # Find the target to get revenue_date and metadata
        target = next((t for t in st.session_state.targets if t.id == entry.target_id), None)
        if not target:
            continue

        partner_name = st.session_state.partners.get(entry.partner_id, entry.partner_id)

        rows.append({
            "partner_id": entry.partner_id,
            "partner_name": partner_name,
            "attributed_amount": entry.attributed_value,
            "split_percent": entry.split_percentage,
            "revenue_date": target.timestamp.date() if isinstance(target.timestamp, datetime) else target.timestamp,
            "account_id": target.metadata.get("account_id", "unknown"),
            "accounts_influenced": 1  # Placeholder - would aggregate in real implementation
        })

    return pd.DataFrame(rows)


def get_revenue_as_dataframe() -> pd.DataFrame:
    """
    Convert targets to revenue DataFrame for dashboard queries.
    """
    if not st.session_state.targets:
        return pd.DataFrame(columns=["revenue_date", "amount", "account_id"])

    rows = []
    for target in st.session_state.targets:
        rows.append({
            "revenue_date": target.timestamp.date() if isinstance(target.timestamp, datetime) else target.timestamp,
            "amount": target.value,
            "account_id": target.metadata.get("account_id", "unknown")
        })

    return pd.DataFrame(rows)


def apply_global_filters(ledger_entries: List[LedgerEntry]) -> List[LedgerEntry]:
    """
    Apply global filters to ledger entries.
    Returns filtered list based on sidebar filter selections.
    """
    filtered = ledger_entries

    # Date range filter
    if st.session_state.global_filters["date_range"]:
        start_date, end_date = st.session_state.global_filters["date_range"]
        # Convert to datetime for comparison
        start_dt = datetime.combine(start_date, datetime.min.time()) if isinstance(start_date, date) else start_date
        end_dt = datetime.combine(end_date, datetime.max.time()) if isinstance(end_date, date) else end_date

        filtered = [
            entry for entry in filtered
            if start_dt <= entry.calculation_timestamp <= end_dt
        ]

    # Partner filter
    if st.session_state.global_filters["selected_partners"]:
        filtered = [
            entry for entry in filtered
            if entry.partner_id in st.session_state.global_filters["selected_partners"]
        ]

    # Min deal size filter
    if st.session_state.global_filters["min_deal_size"] > 0:
        filtered = [
            entry for entry in filtered
            if entry.attributed_value >= st.session_state.global_filters["min_deal_size"]
        ]

    return filtered


def export_ledger_to_csv(ledger_entries: List[LedgerEntry]) -> str:
    """Convert ledger entries to CSV format for download."""
    if not ledger_entries:
        return "partner_id,partner_name,attributed_value,split_percentage,target_id,calculation_timestamp\n"

    rows = []
    for entry in ledger_entries:
        partner_name = st.session_state.partners.get(entry.partner_id, entry.partner_id)
        rows.append({
            "partner_id": entry.partner_id,
            "partner_name": partner_name,
            "attributed_value": entry.attributed_value,
            "split_percentage": entry.split_percentage,
            "target_id": entry.target_id,
            "rule_id": entry.rule_id,
            "calculation_timestamp": entry.calculation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })

    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


# ============================================================================
# Main App
# ============================================================================

st.title("🎯 Attribution MVP - Universal Architecture")
st.caption("Config-driven partner attribution with CSV upload, templates, and natural language rules")

# Sidebar stats and filters
with st.sidebar:
    # Show user info
    render_user_info_sidebar()

    st.markdown("### 🔍 Global Filters")
    st.caption("Apply filters to all dashboards")

    # Date range filter
    date_range = st.date_input(
        "📅 Date Range",
        value=st.session_state.global_filters["date_range"],
        key="date_range_input",
        help="Filter data by date range"
    )
    if date_range and len(date_range) == 2:
        st.session_state.global_filters["date_range"] = date_range

    # Partner filter
    partner_tuples = sorted(
        [(pid, name) for pid, name in st.session_state.partners.items()],
        key=lambda x: x[1]
    )
    partner_display = [f"{name} ({pid})" for pid, name in partner_tuples]

    selected_partners_display = st.multiselect(
        "👥 Partners",
        options=partner_display,
        default=[] if not st.session_state.global_filters["selected_partners"] else [
            f"{st.session_state.partners.get(pid, pid)} ({pid})"
            for pid in st.session_state.global_filters["selected_partners"]
        ],
        help="Filter by specific partners (leave empty for all)"
    )

    # Extract partner IDs from display strings
    if selected_partners_display:
        selected_pids = []
        for display_str in selected_partners_display:
            if "(" in display_str and ")" in display_str:
                # Extract PID from "Partner Name (P001)" format
                pid = display_str.split("(")[-1].replace(")", "")
                selected_pids.append(pid)
        st.session_state.global_filters["selected_partners"] = selected_pids
    else:
        st.session_state.global_filters["selected_partners"] = []

    # Min deal size filter
    min_deal_size = st.number_input(
        "💰 Min Deal Size",
        min_value=0,
        value=st.session_state.global_filters["min_deal_size"],
        step=1000,
        help="Show only deals above this value"
    )
    st.session_state.global_filters["min_deal_size"] = min_deal_size

    # Show active filter count
    active_filters = 0
    if st.session_state.global_filters["selected_partners"]:
        active_filters += 1
    if st.session_state.global_filters["min_deal_size"] > 0:
        active_filters += 1

    if active_filters > 0:
        st.info(f"🎯 {active_filters} filter(s) active")

    # Reset filters button
    if st.button("🔄 Reset Filters", width='stretch'):
        st.session_state.global_filters = {
            "date_range": (datetime.now() - timedelta(days=90), datetime.now()),
            "selected_partners": [],
            "deal_stage": "All",
            "min_deal_size": 0
        }
        st.rerun()

    st.markdown("---")

    st.markdown("### 📊 Quick Stats")
    # Apply filters to show filtered stats
    filtered_ledger = apply_global_filters(st.session_state.ledger)
    filtered_revenue = sum(entry.attributed_value for entry in filtered_ledger)

    st.metric("Targets Loaded", len(st.session_state.targets))
    st.metric("Ledger Entries", f"{len(filtered_ledger)} / {len(st.session_state.ledger)}")
    st.metric("Filtered Revenue", f"${filtered_revenue:,.0f}")
    st.metric("Active Rules", len([r for r in st.session_state.rules if r.active]))

    st.markdown("---")
    st.markdown("### 🏗️ Architecture")
    st.info(f"""
**Schema Version:** {SCHEMA_VERSION}

**Tables:**
- AttributionTarget
- PartnerTouchpoint
- AttributionRule
- AttributionLedger
    """)


# Main tabs - Simplified 5-tab structure (Dreamdata-inspired)
tabs = st.tabs([
    "📊 Dashboard",      # Tab 0: KPIs, charts, overview
    "🔀 Attribution",    # Tab 1: Journey view, deals, models
    "🤝 Partners",       # Tab 2: Partner management & health
    "⚙️ Rules",          # Tab 3: Rule builder & templates
    "🔧 Admin"           # Tab 4: Data import, integrations, settings
])


# ============================================================================
# TAB 0: DASHBOARD (Dreamdata-style)
# ============================================================================

with tabs[0]:
    st.header("📊 Revenue Attribution Dashboard")

    # Get data for KPIs
    revenue_df = get_revenue_as_dataframe()
    attribution_df = get_ledger_as_dataframe()

    # Create DataFrames for the new dashboard functions
    # Convert touchpoints to DataFrame format
    touchpoints_data = []
    for tp in st.session_state.touchpoints:
        touchpoints_data.append({
            'id': tp.id,
            'target_id': tp.target_id,
            'partner_id': tp.partner_id,
            'touchpoint_type': tp.touchpoint_type.value if hasattr(tp.touchpoint_type, 'value') else str(tp.touchpoint_type),
            'timestamp': tp.timestamp,
            'actor_type': 'partner',  # Legacy touchpoints are partner type
            'actor_id': tp.partner_id,
            'actor_name': st.session_state.partners.get(tp.partner_id, tp.partner_id),
            'weight': tp.weight
        })
    touchpoints_df = pd.DataFrame(touchpoints_data) if touchpoints_data else pd.DataFrame()

    # Convert targets to DataFrame
    targets_data = []
    for t in st.session_state.targets:
        targets_data.append({
            'id': t.id,
            'name': t.name,
            'value': t.value,
            'stage': t.metadata.get('stage', 'Unknown'),
            'account_name': t.metadata.get('account_name', t.name),
            'revenue_type': t.metadata.get('revenue_type', 'new_logo'),
            'created_at': t.timestamp,
            'closed_at': t.metadata.get('closed_at')
        })
    targets_df = pd.DataFrame(targets_data) if targets_data else pd.DataFrame()

    # Convert ledger to DataFrame for new functions
    ledger_data = []
    for entry in st.session_state.ledger:
        ledger_data.append({
            'id': entry.id,
            'target_id': entry.target_id,
            'partner_id': entry.partner_id,
            'attributed_value': entry.attributed_value,
            'split_percentage': entry.split_percentage,
            'calculation_timestamp': entry.calculation_timestamp
        })
    ledger_df = pd.DataFrame(ledger_data) if ledger_data else pd.DataFrame()

    # KPI Cards Row (Dreamdata-style)
    if not ledger_df.empty or not touchpoints_df.empty:
        metrics = calculate_kpi_metrics(ledger_df, touchpoints_df, targets_df)
        render_kpi_cards(metrics)
    else:
        # Show placeholder metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Attributed Revenue", "$0")
        with col2:
            st.metric("Total Deals", "0")
        with col3:
            st.metric("Avg Deal Size", "$0")
        with col4:
            st.metric("Avg Touches/Deal", "0")
        with col5:
            st.metric("Top Contributor", "N/A")

    st.markdown("---")

    # Main Charts
    if len(st.session_state.targets) > 0 and len(st.session_state.ledger) > 0:
        # Row 1: Revenue over time + Attribution by actor
        col1, col2 = st.columns(2)

        with col1:
            fig = create_revenue_over_time_chart(revenue_df)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if not touchpoints_df.empty and not ledger_df.empty:
                fig = create_revenue_by_actor_type_chart(touchpoints_df, ledger_df)
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig = create_partner_performance_bar_chart(attribution_df)
                st.plotly_chart(fig, use_container_width=True)

        # Row 2: Attribution breakdown + Deal distribution
        col1, col2 = st.columns(2)

        with col1:
            fig = create_attribution_pie_chart(attribution_df)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = create_deal_value_distribution(revenue_df)
            st.plotly_chart(fig, use_container_width=True)

        # Row 3: Sankey flow (if we have actor data)
        if not touchpoints_df.empty and not ledger_df.empty and not targets_df.empty:
            st.subheader("Revenue Flow")
            fig = create_revenue_relationship_sankey(touchpoints_df, targets_df, ledger_df)
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("📊 **No data to display.** Import data in the Admin tab or load demo data to see the dashboard.")

        if st.button("🎲 Load Demo Data", key="demo_dashboard"):
            with st.spinner("Generating demo data..."):
                targets, touchpoints, rules = generate_complete_demo_data()
                for t in targets:
                    st.session_state.session_manager.add_target(t)
                for tp in touchpoints:
                    st.session_state.session_manager.add_touchpoint(tp)
                for r in rules:
                    st.session_state.session_manager.add_rule(r)
                calculate_attribution_for_all_targets()
            st.success("Demo data loaded!")
            st.rerun()


# ============================================================================
# TAB 1: ATTRIBUTION (Journey view, deals, models)
# ============================================================================

with tabs[1]:
    st.header("🔀 Attribution Analysis")

    # Sub-tabs for different views
    attr_tabs = st.tabs(["📈 Journey View", "🎯 Deal Drilldown", "⚖️ Model Comparison"])

    # Prepare data
    touchpoints_data = []
    for tp in st.session_state.touchpoints:
        touchpoints_data.append({
            'id': tp.id,
            'target_id': tp.target_id,
            'partner_id': tp.partner_id,
            'touchpoint_type': tp.touchpoint_type.value if hasattr(tp.touchpoint_type, 'value') else str(tp.touchpoint_type),
            'timestamp': tp.timestamp,
            'actor_type': 'partner',
            'actor_id': tp.partner_id,
            'actor_name': st.session_state.partners.get(tp.partner_id, tp.partner_id),
            'weight': tp.weight
        })
    touchpoints_df = pd.DataFrame(touchpoints_data) if touchpoints_data else pd.DataFrame()

    targets_data = []
    for t in st.session_state.targets:
        targets_data.append({
            'id': t.id,
            'name': t.name,
            'value': t.value,
            'stage': t.metadata.get('stage', 'Unknown'),
            'account_name': t.metadata.get('account_name', t.name),
            'revenue_type': t.metadata.get('revenue_type', 'new_logo')
        })
    targets_df = pd.DataFrame(targets_data) if targets_data else pd.DataFrame()

    ledger_data = []
    for entry in st.session_state.ledger:
        ledger_data.append({
            'id': entry.id,
            'target_id': entry.target_id,
            'partner_id': entry.partner_id,
            'attributed_value': entry.attributed_value,
            'split_percentage': entry.split_percentage
        })
    ledger_df = pd.DataFrame(ledger_data) if ledger_data else pd.DataFrame()

    # Journey View
    with attr_tabs[0]:
        st.subheader("Customer Journey Timeline")

        if not touchpoints_df.empty:
            # Show aggregated journey timeline
            fig = create_journey_timeline(touchpoints_df)
            st.plotly_chart(fig, use_container_width=True)

            # Contribution trend
            if not ledger_df.empty:
                st.subheader("Contribution Trends Over Time")
                fig = create_actor_contribution_trend(touchpoints_df, ledger_df)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No touchpoint data available. Import data to see journey timelines.")

    # Deal Drilldown
    with attr_tabs[1]:
        st.subheader("Deal-Level Attribution")

        if st.session_state.targets:
            # Deal selector
            deal_options = {t.id: f"{t.name} - ${t.value:,.0f}" for t in st.session_state.targets}
            selected_deal_id = st.selectbox(
                "Select a deal to analyze",
                options=list(deal_options.keys()),
                format_func=lambda x: deal_options[x]
            )

            if selected_deal_id:
                # Get deal details
                selected_target = next((t for t in st.session_state.targets if t.id == selected_deal_id), None)

                if selected_target:
                    # Deal info cards
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Deal Value", f"${selected_target.value:,.0f}")
                    with col2:
                        st.metric("Stage", selected_target.metadata.get('stage', 'Unknown'))
                    with col3:
                        touches = len([tp for tp in st.session_state.touchpoints if tp.target_id == selected_deal_id])
                        st.metric("Touchpoints", touches)
                    with col4:
                        attributions = len([e for e in st.session_state.ledger if e.target_id == selected_deal_id])
                        st.metric("Attributions", attributions)

                    st.markdown("---")

                    # Journey timeline for this deal
                    if not touchpoints_df.empty:
                        st.subheader("Deal Journey")
                        fig = create_journey_timeline(touchpoints_df, target_id=selected_deal_id)
                        st.plotly_chart(fig, use_container_width=True)

                    # Attribution breakdown
                    deal_ledger = [e for e in st.session_state.ledger if e.target_id == selected_deal_id]
                    if deal_ledger:
                        st.subheader("Attribution Breakdown")
                        breakdown_data = []
                        for entry in deal_ledger:
                            partner_name = st.session_state.partners.get(entry.partner_id, entry.partner_id)
                            breakdown_data.append({
                                "Partner": partner_name,
                                "Attributed Value": f"${entry.attributed_value:,.0f}",
                                "Split %": f"{entry.split_percentage:.1f}%",
                                "Rule": entry.rule_id
                            })
                        st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True)
        else:
            st.info("No deals available. Import data to analyze deal-level attribution.")

    # Model Comparison
    with attr_tabs[2]:
        st.subheader("Attribution Model Comparison")
        st.caption("See how different attribution models would credit your actors")

        if not touchpoints_df.empty and not targets_df.empty:
            # Option to compare for specific deal or all deals
            compare_mode = st.radio(
                "Compare mode",
                ["All Deals (Aggregated)", "Single Deal"],
                horizontal=True
            )

            if compare_mode == "Single Deal" and st.session_state.targets:
                deal_options = {t.id: f"{t.name} - ${t.value:,.0f}" for t in st.session_state.targets}
                selected_id = st.selectbox(
                    "Select deal",
                    options=list(deal_options.keys()),
                    format_func=lambda x: deal_options[x],
                    key="model_compare_deal"
                )
                fig = create_attribution_model_comparison(touchpoints_df, targets_df, target_id=selected_id)
            else:
                fig = create_attribution_model_comparison(touchpoints_df, targets_df)

            st.plotly_chart(fig, use_container_width=True)

            # Model descriptions
            with st.expander("📖 Attribution Model Definitions"):
                st.markdown("""
                **First Touch**: 100% credit to the first actor who touched the deal.

                **Last Touch**: 100% credit to the last actor before close.

                **Linear**: Equal credit distributed across all touchpoints.

                **W-Shaped**: 40% to first touch, 40% to last touch, 20% distributed among middle touches.
                """)
        else:
            st.info("No touchpoint data available for model comparison.")


# ============================================================================
# TAB 2: PARTNERS
# ============================================================================

with tabs[2]:
    st.header("🤝 Partner Management")

    partner_tabs = st.tabs(["📊 Performance", "❤️ Health Scores", "📋 Directory"])

    # Performance tab
    with partner_tabs[0]:
        st.subheader("Partner Performance")

        attribution_df = get_ledger_as_dataframe()

        if not attribution_df.empty:
            # Top performers
            partner_summary = attribution_df.groupby('partner_name').agg({
                'attributed_amount': 'sum',
                'partner_id': 'count'
            }).reset_index()
            partner_summary.columns = ['Partner', 'Total Attributed', 'Deal Count']
            partner_summary = partner_summary.sort_values('Total Attributed', ascending=False)

            col1, col2 = st.columns(2)

            with col1:
                fig = create_partner_performance_bar_chart(attribution_df)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = create_partner_role_distribution(attribution_df)
                st.plotly_chart(fig, use_container_width=True)

            # Partner table
            st.subheader("Partner Summary")
            partner_summary['Total Attributed'] = partner_summary['Total Attributed'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(partner_summary, use_container_width=True)
        else:
            st.info("No attribution data available.")

    # Health Scores tab
    with partner_tabs[1]:
        st.subheader("Partner Health Scores")

        if st.session_state.partners and st.session_state.ledger:
            health_data = []
            for pid, pname in st.session_state.partners.items():
                partner_entries = [e for e in st.session_state.ledger if e.partner_id == pid]
                if partner_entries:
                    total_value = sum(e.attributed_value for e in partner_entries)
                    deal_count = len(set(e.target_id for e in partner_entries))

                    # Simple health score based on activity
                    health_score = min(100, (deal_count * 20) + (total_value / 10000))

                    health_data.append({
                        'Partner': pname,
                        'Health Score': int(health_score),
                        'Total Revenue': f"${total_value:,.0f}",
                        'Deals': deal_count,
                        'Grade': 'A' if health_score >= 80 else 'B' if health_score >= 60 else 'C' if health_score >= 40 else 'D'
                    })

            if health_data:
                health_df = pd.DataFrame(health_data).sort_values('Health Score', ascending=False)

                # Health score distribution
                col1, col2, col3, col4 = st.columns(4)
                grades = health_df['Grade'].value_counts()
                with col1:
                    st.metric("A Grade", grades.get('A', 0))
                with col2:
                    st.metric("B Grade", grades.get('B', 0))
                with col3:
                    st.metric("C Grade", grades.get('C', 0))
                with col4:
                    st.metric("D Grade", grades.get('D', 0))

                st.dataframe(health_df, use_container_width=True)
            else:
                st.info("No partner activity data available.")
        else:
            st.info("No partners or attribution data available.")

    # Directory tab
    with partner_tabs[2]:
        st.subheader("Partner Directory")

        if st.session_state.partners:
            partner_list = [{"ID": pid, "Name": pname} for pid, pname in st.session_state.partners.items()]
            st.dataframe(pd.DataFrame(partner_list), use_container_width=True)

            # Add new partner
            st.markdown("---")
            st.subheader("Add Partner")
            col1, col2 = st.columns(2)
            with col1:
                new_pid = st.text_input("Partner ID", placeholder="P009")
            with col2:
                new_pname = st.text_input("Partner Name", placeholder="New Partner Inc")

            if st.button("Add Partner", type="primary"):
                if new_pid and new_pname:
                    st.session_state.session_manager.add_partner(new_pid, new_pname)
                    st.success(f"Added partner: {new_pname}")
                    st.rerun()
                else:
                    st.error("Please provide both ID and name")
        else:
            st.info("No partners in the system.")


# ============================================================================
# TAB 3: RULES
# ============================================================================

with tabs[3]:
    st.header("⚙️ Attribution Rules")

    rules_tabs = st.tabs(["📋 Active Rules", "🎨 Rule Builder", "📦 Templates"])

    # Active Rules
    with rules_tabs[0]:
        st.subheader("Active Attribution Rules")

        if st.session_state.rules:
            for rule in st.session_state.rules:
                with st.expander(f"{'✅' if rule.active else '❌'} {rule.name}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Model:** {rule.model.value}")
                        st.write(f"**Priority:** {rule.priority}")
                        st.write(f"**Active:** {rule.active}")
                    with col2:
                        st.write(f"**Description:** {rule.description}")
                        if rule.conditions:
                            st.write(f"**Conditions:** {json.dumps(rule.conditions, indent=2)}")

                    # Toggle active status
                    if st.button(f"{'Deactivate' if rule.active else 'Activate'}", key=f"toggle_{rule.id}"):
                        rule.active = not rule.active
                        st.session_state.session_manager.update_rule(rule)
                        st.rerun()
        else:
            st.info("No rules defined. Use the Rule Builder or Templates to create rules.")

    # Rule Builder
    with rules_tabs[1]:
        st.subheader("Create New Rule")

        col1, col2 = st.columns(2)

        with col1:
            rule_name = st.text_input("Rule Name", placeholder="Enterprise Partner Split")
            rule_desc = st.text_area("Description", placeholder="Describe what this rule does...")

            model_options = [m.value for m in AttributionModel]
            selected_model = st.selectbox("Attribution Model", model_options)

        with col2:
            priority = st.number_input("Priority", min_value=1, max_value=100, value=10)

            # Conditions
            st.markdown("**Conditions (optional)**")
            min_value = st.number_input("Minimum Deal Value", min_value=0, value=0)
            partner_role = st.selectbox("Partner Role", ["Any"] + list(DEFAULT_PARTNER_ROLES))

        if st.button("Create Rule", type="primary"):
            if rule_name:
                conditions = {}
                if min_value > 0:
                    conditions['min_value'] = min_value
                if partner_role != "Any":
                    conditions['partner_role'] = partner_role

                new_rule = AttributionRule(
                    id=len(st.session_state.rules) + 1,
                    name=rule_name,
                    description=rule_desc,
                    model=AttributionModel(selected_model),
                    priority=priority,
                    conditions=conditions,
                    active=True
                )
                st.session_state.session_manager.add_rule(new_rule)
                st.success(f"Created rule: {rule_name}")
                st.rerun()
            else:
                st.error("Please provide a rule name")

    # Templates
    with rules_tabs[2]:
        st.subheader("Rule Templates")
        st.caption("Quick-start with pre-built attribution rules")

        templates = list_templates()

        for template in templates:
            with st.expander(f"📦 {template['name']}", expanded=False):
                st.write(f"**Description:** {template.get('description', 'No description')}")
                st.write(f"**Model:** {template.get('model', 'Unknown')}")

                if st.button(f"Apply Template", key=f"apply_{template['name']}"):
                    template_data = get_template(template['name'])
                    if template_data:
                        new_rule = AttributionRule(
                            id=len(st.session_state.rules) + 1,
                            name=template_data.get('name', template['name']),
                            description=template_data.get('description', ''),
                            model=AttributionModel(template_data.get('model', 'equal_split')),
                            priority=template_data.get('priority', 10),
                            conditions=template_data.get('conditions', {}),
                            active=True
                        )
                        st.session_state.session_manager.add_rule(new_rule)
                        st.success(f"Applied template: {template['name']}")
                        st.rerun()


# ============================================================================
# TAB 4: ADMIN
# ============================================================================

with tabs[4]:
    st.header("🔧 Admin & Settings")

    admin_tabs = st.tabs(["📥 Data Import", "🔄 Actions", "📜 Audit Log", "⚙️ Settings"])

    # Data Import
    with admin_tabs[0]:
        st.subheader("Data Import")

        # CSV Upload
        st.markdown("### Upload CSV")
        uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.write("Preview:")
                st.dataframe(df.head())

                # Detect schema
                detector = SchemaDetector()
                schema_type = detector.detect(df)
                st.info(f"Detected schema type: **{schema_type}**")

                if st.button("Import Data", type="primary"):
                    with st.spinner("Importing..."):
                        result = ingest_csv(df, st.session_state.session_manager)
                        st.success(f"Imported {result.get('targets', 0)} targets, {result.get('touchpoints', 0)} touchpoints")
                        st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")

        st.markdown("---")

        # Download templates
        st.markdown("### Download Templates")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Deals Template"):
                template = generate_csv_template('deals')
                st.download_button("Download", template, "deals_template.csv", "text/csv")
        with col2:
            if st.button("📄 Touchpoints Template"):
                template = generate_csv_template('touchpoints')
                st.download_button("Download", template, "touchpoints_template.csv", "text/csv")

    # Actions
    with admin_tabs[1]:
        st.subheader("Actions")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Recalculate Attribution")
            st.caption("Re-run attribution calculations using current rules")
            if st.button("🔄 Recalculate All", type="primary"):
                with st.spinner("Recalculating..."):
                    count = calculate_attribution_for_all_targets()
                    st.success(f"Created {count} attribution entries")
                    st.rerun()

        with col2:
            st.markdown("### Demo Data")
            st.caption("Load sample data for testing")
            if st.button("🎲 Load Demo Data"):
                with st.spinner("Generating demo data..."):
                    targets, touchpoints, rules = generate_complete_demo_data()
                    for t in targets:
                        st.session_state.session_manager.add_target(t)
                    for tp in touchpoints:
                        st.session_state.session_manager.add_touchpoint(tp)
                    for r in rules:
                        st.session_state.session_manager.add_rule(r)
                    calculate_attribution_for_all_targets()
                st.success("Demo data loaded!")
                st.rerun()

        st.markdown("---")

        st.markdown("### Danger Zone")
        st.caption("⚠️ These actions cannot be undone")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All Data", type="secondary"):
                st.session_state.session_manager.clear_all_data()
                st.success("All data cleared")
                st.rerun()

        with col2:
            if st.button("🔄 Reset Database", type="secondary"):
                import os
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                st.success("Database reset. Please refresh the page.")

    # Audit Log
    with admin_tabs[2]:
        st.subheader("Attribution Ledger (Audit Trail)")

        if st.session_state.ledger:
            ledger_data = []
            for entry in st.session_state.ledger:
                target = next((t for t in st.session_state.targets if t.id == entry.target_id), None)
                partner_name = st.session_state.partners.get(entry.partner_id, entry.partner_id)
                ledger_data.append({
                    "ID": entry.id,
                    "Target": target.name if target else f"Target {entry.target_id}",
                    "Partner": partner_name,
                    "Value": f"${entry.attributed_value:,.0f}",
                    "Split %": f"{entry.split_percentage:.1f}%",
                    "Timestamp": entry.calculation_timestamp.strftime("%Y-%m-%d %H:%M")
                })

            st.dataframe(pd.DataFrame(ledger_data), use_container_width=True)

            # Export
            csv_data = export_ledger_to_csv(st.session_state.ledger)
            st.download_button("📥 Export Ledger CSV", csv_data, "attribution_ledger.csv", "text/csv")
        else:
            st.info("No ledger entries yet.")

    # Settings
    with admin_tabs[3]:
        st.subheader("Settings")

        st.markdown("### Attribution Settings")

        enforce_cap = st.checkbox(
            "Enforce 100% Split Cap",
            value=True,
            help="Prevent total attribution splits from exceeding 100%"
        )

        default_model = st.selectbox(
            "Default Attribution Model",
            [m.value for m in AttributionModel],
            help="Model used when no specific rule matches"
        )

        st.markdown("---")

        st.markdown("### System Info")
        st.info(f"""
        **Schema Version:** {SCHEMA_VERSION}
        **Database:** {DB_PATH}
        **Targets:** {len(st.session_state.targets)}
        **Touchpoints:** {len(st.session_state.touchpoints)}
        **Rules:** {len(st.session_state.rules)}
        **Ledger Entries:** {len(st.session_state.ledger)}
        """)
