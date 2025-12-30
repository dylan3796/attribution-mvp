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

# New universal architecture imports
from models_new import (
    AttributionTarget, PartnerTouchpoint, AttributionRule, LedgerEntry,
    TargetType, TouchpointType, AttributionModel, SplitConstraint,
    DEFAULT_PARTNER_ROLES, SCHEMA_VERSION
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
    create_attribution_waterfall
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

/* Button styling for better visibility in both themes */
.stButton > button {
    border: 2px solid rgba(150, 150, 150, 0.3) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    border-color: rgba(100, 100, 255, 0.5) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
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
# In-Memory Data Store (SQLite integration would go here)
# ============================================================================

# Initialize session state for data storage
if "targets" not in st.session_state:
    st.session_state.targets = []  # List[AttributionTarget]

if "touchpoints" not in st.session_state:
    st.session_state.touchpoints = []  # List[PartnerTouchpoint]

if "rules" not in st.session_state:
    st.session_state.rules = []  # List[AttributionRule]

if "ledger" not in st.session_state:
    st.session_state.ledger = []  # List[LedgerEntry]

if "partners" not in st.session_state:
    # Preserve existing partner data for dashboard compatibility
    st.session_state.partners = {
        "P001": "CloudConsult Partners",
        "P002": "DataWorks SI",
        "P003": "AnalyticsPro",
        "P004": "TechAlliance Inc",
        "P005": "InnovateCo",
        "P006": "SystemsPartner LLC",
        "P007": "GlobalTech Solutions",
        "P008": "EnterprisePartners"
    }

# Global filters state
if "global_filters" not in st.session_state:
    st.session_state.global_filters = {
        "date_range": (datetime.now() - timedelta(days=90), datetime.now()),
        "selected_partners": [],
        "deal_stage": "All",
        "min_deal_size": 0
    }

# Metric visibility toggles
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
    Populates the ledger.
    """
    engine = AttributionEngine()

    new_ledger_entries = []

    for target in st.session_state.targets:
        # Get touchpoints for this target
        target_touchpoints = [
            tp for tp in st.session_state.touchpoints
            if tp.target_id == target.id
        ]

        if not target_touchpoints:
            continue

        # Select best rule for this target
        rule = select_rule_for_target(target, st.session_state.rules)

        if not rule:
            continue

        # Calculate attribution
        entries = engine.calculate(target, target_touchpoints, rule)

        new_ledger_entries.extend(entries)

    # Append to ledger (immutable - never delete old entries)
    st.session_state.ledger.extend(new_ledger_entries)

    return len(new_ledger_entries)


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
    st.markdown("### 🔍 Global Filters")
    st.caption("Apply filters to all dashboards")

    # Date range filter
    date_range = st.date_input(
        "📅 Date Range",
        value=st.session_state.global_filters["date_range"],
        key="date_range_input",
        help="Filter data by date range"
    )
    if len(date_range) == 2:
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
    if st.button("🔄 Reset Filters", use_container_width=True):
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


# Main tabs - Organized by role/workflow
tabs = st.tabs([
    # 🎯 OPERATIONAL VIEWS (Daily Use)
    "📊 Executive Dashboard",      # Tab 0: C-suite overview
    "💼 Partner Sales",            # Tab 1: Partner performance & revenue
    "🤝 Partner Management",       # Tab 2: Partner health & alerts
    "💰 Deal Drilldown",           # Tab 3: Dispute resolution

    # ⚙️ SETUP & CONFIGURATION (Admin - Ordered by ease of use)
    "📥 Data Import",              # Tab 4: Upload data (first step)
    "🎨 Rule Builder",             # Tab 5: Visual rule creator (easy, no-code)
    "📋 Rules & Templates",        # Tab 6: Manage existing rules
    "🔄 Measurement Workflows",    # Tab 7: Advanced attribution methods

    # 🔍 ADVANCED (Audit & Deep Dive)
    "🔍 Ledger Explorer"           # Tab 8: Immutable audit trail
])


# ============================================================================
# TAB 0: DASHBOARD (PRESERVED FROM ORIGINAL)
# ============================================================================

with tabs[0]:
    col_title, col_export, col_customize = st.columns([3, 1, 1])

    with col_title:
        st.title("📊 Executive Dashboard")
        st.caption("Executive overview of partner attribution performance and metrics")

    with col_export:
        st.markdown("") # Spacing
        if st.button("📥 Export CSV", key="exec_export", use_container_width=True):
            filtered_ledger = apply_global_filters(st.session_state.ledger)
            csv_data = export_ledger_to_csv(filtered_ledger)
            st.download_button(
                "Download Data",
                csv_data,
                "executive_dashboard.csv",
                "text/csv",
                key="exec_download"
            )

    with col_customize:
        st.markdown("") # Spacing
        with st.popover("⚙️ Metrics", use_container_width=True):
            st.markdown("**Show/Hide Metrics**")
            st.session_state.visible_metrics["revenue"] = st.checkbox(
                "Total Revenue",
                value=st.session_state.visible_metrics["revenue"]
            )
            st.session_state.visible_metrics["deal_count"] = st.checkbox(
                "Deal Count",
                value=st.session_state.visible_metrics["deal_count"]
            )
            st.session_state.visible_metrics["active_partners"] = st.checkbox(
                "Active Partners",
                value=st.session_state.visible_metrics["active_partners"]
            )
            st.session_state.visible_metrics["avg_deal_size"] = st.checkbox(
                "Avg Deal Size",
                value=st.session_state.visible_metrics["avg_deal_size"]
            )

    # Use global filters from sidebar
    start_date, end_date = st.session_state.global_filters["date_range"]

    # Convert date to datetime if needed
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, datetime.min.time())
    if isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, datetime.max.time())

    # Show current filter info
    period_days = (end_date - start_date).days + 1
    st.info(f"📅 Showing data for: **{start_date.strftime('%b %d, %Y')}** to **{end_date.strftime('%b %d, %Y')}** ({period_days} days) • Change filters in sidebar")

    # Get data using new architecture
    with st.spinner("📊 Loading dashboard data..."):
        try:
            revenue_df = get_revenue_as_dataframe()
            attribution_df = get_ledger_as_dataframe()
        except Exception as e:
            st.error("⚠️ **Failed to load dashboard data**")
            st.markdown(f"""
            **Error:** {str(e)}

            **Troubleshooting steps:**
            1. Check if data was imported correctly in the Data Import tab
            2. Verify attribution rules exist in Rules & Templates tab
            3. Try recalculating attribution in Ledger Explorer

            If the issue persists, please refresh the page.
            """)
            st.stop()

    # Show dashboard content only if data is loaded
    if len(st.session_state.targets) > 0:
        # Apply global filters
        filtered_ledger = apply_global_filters(st.session_state.ledger)

        # Convert filtered ledger back to DataFrame
        if filtered_ledger:
            filtered_rows = []
            for entry in filtered_ledger:
                target = next((t for t in st.session_state.targets if t.id == entry.target_id), None)
                if not target:
                    continue
                partner_name = st.session_state.partners.get(entry.partner_id, entry.partner_id)
                filtered_rows.append({
                    "partner_id": entry.partner_id,
                    "partner_name": partner_name,
                    "attributed_amount": entry.attributed_value,
                    "split_percent": entry.split_percentage,
                    "revenue_date": target.timestamp.date() if isinstance(target.timestamp, datetime) else target.timestamp,
                    "account_id": target.metadata.get("account_id", "unknown"),
                    "accounts_influenced": 1
                })
            attribution_df = pd.DataFrame(filtered_rows)
        else:
            attribution_df = pd.DataFrame(columns=["partner_id", "partner_name", "attributed_amount", "split_percent", "revenue_date", "account_id"])

        # Filter revenue by date range
        if not revenue_df.empty:
            revenue_df = revenue_df[
                (pd.to_datetime(revenue_df["revenue_date"]) >= pd.to_datetime(start_date)) &
                (pd.to_datetime(revenue_df["revenue_date"]) <= pd.to_datetime(end_date))
            ]

        # Aggregate attribution by partner (for charts)
        if not attribution_df.empty:
            attribution_agg = attribution_df.groupby(["partner_id", "partner_name"]).agg({
                "attributed_amount": "sum",
                "split_percent": "mean",
                "account_id": "nunique"
            }).reset_index()
            attribution_agg.columns = ["partner_id", "partner_name", "attributed_amount", "avg_split_percent", "accounts_influenced"]
        else:
            attribution_agg = pd.DataFrame(columns=["partner_id", "partner_name", "attributed_amount", "avg_split_percent", "accounts_influenced"])

        # KEY METRICS ROW (PRESERVED)
        st.markdown("### Key Metrics")
        metric_cols = st.columns(5)

        total_revenue = float(revenue_df["amount"].sum()) if not revenue_df.empty else 0.0
        total_attributed = float(attribution_agg["attributed_amount"].sum()) if not attribution_agg.empty else 0.0
        attribution_coverage = (total_attributed / total_revenue * 100) if total_revenue > 0 else 0.0

        with metric_cols[0]:
            period_days = (end_date - start_date).days + 1
            st.metric(
                "Total Revenue",
                f"${total_revenue:,.0f}",
                delta=f"{period_days}d period",
                help="Sum of all closed opportunity/deal values in the selected time period"
            )

        with metric_cols[1]:
            st.metric(
                "Attributed Revenue",
                f"${total_attributed:,.0f}",
                delta=f"{attribution_coverage:.1f}% coverage",
                help="Total revenue attributed to partners based on active attribution rules. Coverage shows % of revenue with partner attribution."
            )

        with metric_cols[2]:
            unique_accounts = revenue_df["account_id"].nunique() if not revenue_df.empty else 0
            st.metric(
                "Active Accounts",
                f"{unique_accounts}",
                delta=f"{len(st.session_state.targets)} targets",
                help="Number of unique customer accounts with closed deals in this period"
            )

        with metric_cols[3]:
            unique_partners = attribution_agg["partner_id"].nunique() if not attribution_agg.empty else 0
            st.metric(
                "Partner Count",
                f"{len(st.session_state.partners)}",
                delta=f"{unique_partners} active",
                help="Total partners in system. 'Active' shows partners with attributed revenue in this period."
            )

        with metric_cols[4]:
            st.metric(
                "Touchpoints",
                f"{len(st.session_state.touchpoints)}",
                delta=f"{len(st.session_state.ledger)} ledger entries",
                help="Total partner interactions/engagements logged. Ledger entries show calculated attribution splits."
            )

        st.markdown("---")

        # CHARTS ROW 1: Revenue and Attribution (PRESERVED)
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
                create_attribution_pie_chart(attribution_agg),
                use_container_width=True,
                key="attribution_pie"
            )

        st.markdown("---")

        # CHARTS ROW 2: Partner Performance (PRESERVED)
        st.markdown("### Partner Performance")
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            st.plotly_chart(
                create_partner_performance_bar_chart(attribution_agg),
                use_container_width=True,
                key="partner_performance"
            )

        with chart_col4:
            # Partner role distribution (need touchpoint data)
            touchpoint_roles_df = pd.DataFrame([
                {"partner_role": tp.role, "partner_id": tp.partner_id, "use_case_id": tp.target_id}
                for tp in st.session_state.touchpoints
            ])

            st.plotly_chart(
                create_partner_role_distribution(touchpoint_roles_df),
                use_container_width=True,
                key="role_distribution"
            )

        st.markdown("---")

        # CHARTS ROW 3: Deal Analysis
        st.markdown("### Deal Analysis")
        chart_col5, chart_col6 = st.columns(2)

        with chart_col5:
            st.plotly_chart(
                create_deal_value_distribution(revenue_df),
                use_container_width=True,
                key="deal_value_dist"
            )

        with chart_col6:
            # Attribution Waterfall
            st.plotly_chart(
                create_attribution_waterfall(attribution_agg, total_revenue),
                use_container_width=True,
                key="waterfall"
            )

        st.markdown("---")

        # EXPORT SECTION (PRESERVED)
        st.markdown("### Export Dashboard Data")
        export_cols = st.columns(4)

        with export_cols[0]:
            if not revenue_df.empty:
                csv_data = export_to_csv(revenue_df, "revenue_data.csv")
                st.download_button(
                    "Download Revenue CSV",
                    data=csv_data,
                    file_name=f"revenue_{start_date}_to_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with export_cols[1]:
            if not attribution_agg.empty:
                excel_data = export_to_excel({
                    "Revenue": revenue_df,
                    "Attribution": attribution_agg
                })
                st.download_button(
                    "Download Excel",
                    data=excel_data,
                    file_name=f"dashboard_{start_date}_to_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        with export_cols[2]:
            if not attribution_agg.empty:
                try:
                    # Generate executive PDF report
                    with st.spinner("📄 Generating executive PDF report..."):
                        ledger_df = get_ledger_as_dataframe()

                        executive_pdf = generate_executive_report(
                            report_date_range=f"{start_date} to {end_date}",
                            total_revenue=total_revenue,
                            total_attributed=total_attributed,
                            attribution_coverage=attribution_coverage,
                            unique_partners=unique_partners,
                            top_partners=attribution_agg,
                            ledger_df=ledger_df
                        )
                    st.download_button(
                        "📊 Executive Report (PDF)",
                        data=executive_pdf,
                        file_name=f"attribution_executive_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        help="Beautiful executive report with charts and insights"
                    )
                except Exception as e:
                    st.error("❌ Failed to generate PDF report")
                    with st.expander("Show error details"):
                        st.code(str(e))
                    st.markdown("""
                    **Try these steps:**
                    1. Ensure attribution data is calculated
                    2. Check that all partners have names
                    3. Try downloading CSV/Excel instead
                    """)
            else:
                st.info("💡 No attribution data available. Import data and run attribution to generate reports.")

        # Top Partners Table (PRESERVED)
        st.markdown("---")
        st.markdown("### Top 10 Partners by Attributed Revenue")
        if not attribution_agg.empty:
            top_10 = attribution_agg.nlargest(10, "attributed_amount")
            st.dataframe(
                top_10[["partner_name", "attributed_amount", "avg_split_percent", "accounts_influenced"]],
                use_container_width=True
            )

        # PARTNER-SPECIFIC REPORTS
        st.markdown("---")
        st.markdown("### 📄 Partner-Specific Reports")
        st.caption("Generate individual attribution statements for each partner")

        if not attribution_agg.empty:
            # INDIVIDUAL PARTNER REPORT
            st.markdown("#### Single Partner Statement")
            partner_report_col1, partner_report_col2 = st.columns([3, 1])

            with partner_report_col1:
                # Partner selector
                partner_options = {
                    f"{row.partner_name} ({row.partner_id})": row.partner_id
                    for _, row in attribution_agg.iterrows()
                }
                selected_partner_display = st.selectbox(
                    "Select Partner",
                    options=list(partner_options.keys()),
                    help="Choose a partner to generate their attribution statement"
                )
                selected_partner_id = partner_options[selected_partner_display]

            with partner_report_col2:
                # Generate button
                partner_name = selected_partner_display.split(" (")[0]
                partner_pdf = generate_partner_statement_pdf(
                    partner_id=selected_partner_id,
                    partner_name=partner_name,
                    ledger_entries=st.session_state.ledger,
                    targets=st.session_state.targets,
                    report_period=f"{start_date} to {end_date}"
                )

                st.download_button(
                    "📥 Download Statement",
                    data=partner_pdf,
                    file_name=f"partner_statement_{selected_partner_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="PDF statement showing this partner's attribution details"
                )

            # BULK EXPORT
            st.markdown("#### Bulk Export (All Partners)")
            bulk_col1, bulk_col2 = st.columns([3, 1])

            with bulk_col1:
                num_partners_with_attr = len(attribution_agg)
                st.info(f"💼 Generate statements for all {num_partners_with_attr} partners with attribution. Perfect for monthly payout processes!")

            with bulk_col2:
                with st.spinner("📦 Generating bulk statements..."):
                    bulk_zip = generate_bulk_partner_statements(
                        ledger_entries=st.session_state.ledger,
                        targets=st.session_state.targets,
                        partners=st.session_state.partners,
                        report_period=f"{start_date} to {end_date}"
                    )

                st.download_button(
                    "📦 Download All (ZIP)",
                    data=bulk_zip,
                    file_name=f"partner_statements_bulk_{datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    help=f"ZIP file containing {num_partners_with_attr} individual partner PDFs"
                )
        else:
            st.info("No partner attribution data available. Load data and run attribution calculations to generate partner reports.")
    else:
        st.info("### 👋 Welcome to Attribution MVP!")
        st.markdown("""
        You haven't loaded any data yet. To get started:

        **Option 1: Try Demo Data (Recommended)**
        1. Click the **"📥 Data Import"** tab above
        2. Click **"🚀 Load Demo Data"** button
        3. Return to this Dashboard to see attribution metrics

        **Option 2: Upload Your Own Data**
        1. Go to **"📥 Data Import"** tab
        2. Upload your target data (opportunities/deals)
        3. Upload partner touchpoint data
        4. Create attribution rules in **"⚙️ Rule Builder"** tab

        **What you'll see here:**
        - 📊 Revenue and attribution metrics
        - 📈 Partner performance charts
        - 🏆 Top contributing partners
        - 📋 Attribution ledger entries
        """)


# ============================================================================
# TAB 1: PARTNER SALES DASHBOARD (NEW)
# ============================================================================

with tabs[1]:
    col_title, col_export = st.columns([4, 1])

    with col_title:
        st.title("💼 Partner Sales Dashboard")
        st.caption("Track revenue growth, performance trends, and actionable insights for partner sales managers")

    with col_export:
        st.markdown("") # Spacing
        if st.button("📥 Export CSV", key="sales_export", use_container_width=True):
            filtered_ledger = apply_global_filters(st.session_state.ledger)
            csv_data = export_ledger_to_csv(filtered_ledger)
            st.download_button(
                "Download Data",
                csv_data,
                "partner_sales_dashboard.csv",
                "text/csv",
                key="sales_download"
            )

    st.markdown("---")

    # Use global filters
    start_date, end_date = st.session_state.global_filters["date_range"]
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, datetime.min.time())
    if isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, datetime.max.time())

    period_days = (end_date - start_date).days + 1
    st.info(f"📅 Showing data for: **{start_date.strftime('%b %d, %Y')}** to **{end_date.strftime('%b %d, %Y')}** ({period_days} days) • Change filters in sidebar")

    # Date Range Selector with Comparison Toggle
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        period_type = st.selectbox(
            "Period Type",
            ["Quick Range", "Month", "Quarter"],
            key="sales_period_type",
            help="Select reporting period"
        )

    with col2:
        if period_type == "Quick Range":
            days = st.selectbox(
                "Time Range",
                [7, 30, 60, 90],
                index=1,
                format_func=lambda x: f"Last {x} days",
                key="sales_days"
            )
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        elif period_type == "Month":
            months = []
            today = date.today()
            for i in range(6):
                month_date = today.replace(day=1) - timedelta(days=i*30)
                months.append((month_date.strftime("%B %Y"), month_date.year, month_date.month))

            selected_month = st.selectbox(
                "Select Month",
                [m[0] for m in months],
                key="sales_month"
            )

            year, month = next((m[1], m[2]) for m in months if m[0] == selected_month)
            start_date = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)
        else:  # Quarter
            quarters = []
            today = date.today()
            current_quarter = (today.month - 1) // 3 + 1
            current_year = today.year

            for i in range(4):
                q = current_quarter - i
                y = current_year
                while q <= 0:
                    q += 4
                    y -= 1
                quarters.append((f"Q{q} {y}", y, q))

            selected_quarter = st.selectbox(
                "Select Quarter",
                [q[0] for q in quarters],
                key="sales_quarter"
            )

            year, quarter = next((q[1], q[2]) for q in quarters if q[0] == selected_quarter)
            start_month = (quarter - 1) * 3 + 1
            start_date = date(year, start_month, 1)
            end_month = start_month + 2
            last_day = calendar.monthrange(year, end_month)[1]
            end_date = date(year, end_month, last_day)

    with col3:
        compare_enabled = st.checkbox(
            "Compare",
            value=True,
            key="sales_compare",
            help="Compare to previous period"
        )

    # Calculate previous period dates if comparison enabled
    if compare_enabled:
        period_days = (end_date - start_date).days + 1
        previous_end = start_date - timedelta(days=1)
        previous_start = previous_end - timedelta(days=period_days - 1)
    else:
        previous_start = previous_end = None

    st.markdown("---")

    # Get data
    if st.session_state.targets and st.session_state.ledger:
        # Calculate period comparison
        if compare_enabled and previous_start and previous_end:
            try:
                comparison = calculate_period_comparison(
                    st.session_state.ledger,
                    st.session_state.targets,
                    start_date,
                    end_date,
                    previous_start,
                    previous_end
                )
            except Exception as e:
                st.error(f"Error calculating period comparison: {str(e)}")
                comparison = None
        else:
            comparison = None

        # Key Metrics Row
        st.markdown("### Key Metrics")
        metric_cols = st.columns(4)

        # Calculate current period metrics
        current_ledger = [
            e for e in st.session_state.ledger
            if start_date <= e.calculation_timestamp.date() <= end_date
        ]
        current_revenue = sum(e.attributed_value for e in current_ledger)
        current_deals = len(set(e.target_id for e in current_ledger))

        current_targets = [
            t for t in st.session_state.targets
            if start_date <= t.timestamp.date() <= end_date
            and t.metadata.get('is_closed', False)
        ]
        total_revenue = sum(t.value for t in current_targets)
        coverage = (current_revenue / total_revenue * 100) if total_revenue > 0 else 0

        with metric_cols[0]:
            if comparison:
                delta = format_growth_percentage(comparison.growth_percentage / 100)
                st.metric("Attributed Revenue", format_currency_compact(current_revenue), delta=delta)
            else:
                st.metric("Attributed Revenue", format_currency_compact(current_revenue))

        with metric_cols[1]:
            if comparison:
                delta = format_growth_percentage(comparison.deal_growth_percentage / 100)
                st.metric("Deals", str(current_deals), delta=delta)
            else:
                st.metric("Deals", str(current_deals))

        with metric_cols[2]:
            if comparison:
                coverage_delta = comparison.current_coverage - comparison.previous_coverage
                delta_str = f"{coverage_delta:+.1f}%"
                st.metric("Coverage", f"{coverage:.1f}%", delta=delta_str)
            else:
                st.metric("Coverage", f"{coverage:.1f}%")

        with metric_cols[3]:
            unique_partners = len(set(e.partner_id for e in current_ledger))
            st.metric("Active Partners", str(unique_partners))

        st.markdown("---")

        # Alerts & Insights Section
        st.markdown("### 🚨 Alerts & Insights")

        try:
            alerts = detect_alerts(
                st.session_state.targets,
                st.session_state.ledger,
                st.session_state.touchpoints,
                st.session_state.partners,
                lookback_days=30
            )

            if alerts:
                for alert in alerts[:3]:  # Show top 3
                    severity_icon = {"critical": "🔴", "warning": "⚠️", "info": "💡"}
                    icon = severity_icon.get(alert.severity, "ℹ️")

                    with st.expander(f"{icon} {alert.title}", expanded=(alert.severity == "critical")):
                        st.markdown(f"**Description:** {alert.description}")
                        if alert.partner_name:
                            st.markdown(f"**Partner:** {alert.partner_name}")
                        st.info(f"💡 **Action:** {alert.recommended_action}")
            else:
                st.success("✅ No alerts. All metrics within expected ranges.")
        except Exception as e:
            st.warning(f"Unable to generate alerts: {str(e)}")

        st.markdown("---")

        # Charts Row
        st.markdown("### Performance Analysis")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            if comparison:
                try:
                    fig = create_period_comparison_chart(comparison, metric_type="revenue")
                    st.plotly_chart(fig, use_container_width=True, key="sales_comparison_chart")
                except Exception as e:
                    st.error(f"Error creating comparison chart: {str(e)}")
            else:
                # Show revenue trend without comparison
                revenue_df = get_revenue_as_dataframe()
                if not revenue_df.empty:
                    filtered_revenue = revenue_df[
                        (pd.to_datetime(revenue_df["revenue_date"]) >= pd.to_datetime(start_date)) &
                        (pd.to_datetime(revenue_df["revenue_date"]) <= pd.to_datetime(end_date))
                    ]
                    st.plotly_chart(
                        create_revenue_over_time_chart(filtered_revenue),
                        use_container_width=True,
                        key="sales_revenue_trend"
                    )

        with chart_col2:
            # Top partners bar chart
            attribution_agg = get_ledger_as_dataframe()
            if not attribution_agg.empty:
                filtered_attr = attribution_agg[
                    (pd.to_datetime(attribution_agg["revenue_date"]) >= pd.to_datetime(start_date)) &
                    (pd.to_datetime(attribution_agg["revenue_date"]) <= pd.to_datetime(end_date))
                ]

                if not filtered_attr.empty:
                    partner_summary = filtered_attr.groupby(["partner_id", "partner_name"]).agg({
                        "attributed_amount": "sum",
                        "account_id": "nunique"
                    }).reset_index()
                    partner_summary.columns = ["partner_id", "partner_name", "attributed_amount", "accounts_influenced"]

                    st.plotly_chart(
                        create_partner_performance_bar_chart(partner_summary),
                        use_container_width=True,
                        key="sales_partner_performance"
                    )

        st.markdown("---")

        # Top Movers Section
        if comparison and previous_start and previous_end:
            st.markdown("### 📈 Top Movers")

            try:
                movers = get_top_movers(
                    st.session_state.ledger,
                    st.session_state.partners,
                    start_date,
                    end_date,
                    previous_start,
                    previous_end
                )

                if movers:
                    # Show top 10 in table
                    movers_data = []
                    for mover in movers[:10]:
                        movers_data.append({
                            "Partner": mover.partner_name,
                            "Current": format_currency_compact(mover.current_revenue),
                            "Previous": format_currency_compact(mover.previous_revenue),
                            "Change": f"{mover.trend_indicator} {format_growth_percentage(mover.change_percentage / 100)}"
                        })

                    st.dataframe(
                        pd.DataFrame(movers_data),
                        use_container_width=True,
                        hide_index=True
                    )

                    # Also show chart
                    st.plotly_chart(
                        create_top_movers_chart(movers, limit=8),
                        use_container_width=True,
                        key="sales_top_movers_chart"
                    )
                else:
                    st.info("No partner activity changes to display")
            except Exception as e:
                st.warning(f"Unable to calculate top movers: {str(e)}")

    else:
        st.info("📊 **No data loaded yet.**\n\nGo to the **Data Import** tab to load demo data or upload your own data.")


# ============================================================================
# TAB 2: PARTNER MANAGEMENT DASHBOARD (NEW)
# ============================================================================

with tabs[2]:
    col_title, col_export = st.columns([4, 1])

    with col_title:
        st.title("🤝 Partner Management Dashboard")
        st.caption("Comprehensive partner health, engagement metrics, and relationship insights for partner account managers")

    with col_export:
        st.markdown("") # Spacing
        if st.button("📥 Export CSV", key="mgmt_export", use_container_width=True):
            filtered_ledger = apply_global_filters(st.session_state.ledger)
            csv_data = export_ledger_to_csv(filtered_ledger)
            st.download_button(
                "Download Data",
                csv_data,
                "partner_management_dashboard.csv",
                "text/csv",
                key="mgmt_download"
            )

    st.markdown("---")

    if not st.session_state.partners:
        st.info("📊 **No partners loaded yet.**\n\nGo to the **Data Import** tab to load demo data or upload your own data.")
    else:
        # Partner Selector
        col1, col2 = st.columns([3, 1])

        with col1:
            # Create partner options sorted by recent revenue
            partner_revenue = {}
            for entry in st.session_state.ledger:
                partner_revenue[entry.partner_id] = partner_revenue.get(entry.partner_id, 0) + entry.attributed_value

            sorted_partners = sorted(
                st.session_state.partners.items(),
                key=lambda x: partner_revenue.get(x[0], 0),
                reverse=True
            )

            selected_partner_id = st.selectbox(
                "Select Partner",
                options=[p[0] for p in sorted_partners],
                format_func=lambda pid: f"{st.session_state.partners[pid]} ({pid})",
                key="mgmt_partner_selector"
            )

            selected_partner_name = st.session_state.partners[selected_partner_id]

        with col2:
            # Show partner since date (first touchpoint)
            partner_tps = [tp for tp in st.session_state.touchpoints if tp.partner_id == selected_partner_id]
            if partner_tps:
                first_tp = min([tp for tp in partner_tps if tp.timestamp], key=lambda tp: tp.timestamp, default=None)
                if first_tp:
                    st.metric("Partner Since", first_tp.timestamp.strftime("%b %Y"))

        st.markdown("---")

        # Calculate Health Score
        try:
            health_score = calculate_health_score(
                selected_partner_id,
                st.session_state.ledger,
                st.session_state.touchpoints,
                st.session_state.targets,
                lookback_days=90
            )

            # Health Score Card
            st.markdown("### Partner Health")

            health_col1, health_col2 = st.columns([1, 2])

            with health_col1:
                # Large health gauge
                fig = create_health_gauge(health_score.total_score, title="Health Score")
                st.plotly_chart(fig, use_container_width=True, key="mgmt_health_gauge")

            with health_col2:
                # Health details card
                health_emoji = get_health_emoji(health_score.total_score)
                grade_desc = get_grade_description(health_score.grade)

                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.75); border: 1px solid #e2e8f0; border-radius: 14px; padding: 1.5rem;">
                    <h3>{health_emoji} {selected_partner_name}</h3>
                    <p style="font-size: 1.2em;"><b>Grade: {health_score.grade}</b> ({grade_desc})</p>
                    <p>Trend: {health_score.trend}</p>
                </div>
                """, unsafe_allow_html=True)

                # Calculate metrics for insights
                partner_ledger = [e for e in st.session_state.ledger if e.partner_id == selected_partner_id]

                cutoff_30d = datetime.now() - timedelta(days=30)
                recent_ledger = [e for e in partner_ledger if e.calculation_timestamp >= cutoff_30d]
                prev_30d_start = datetime.now() - timedelta(days=60)
                prev_30d_end = datetime.now() - timedelta(days=30)
                prev_ledger = [e for e in partner_ledger
                              if prev_30d_start <= e.calculation_timestamp < prev_30d_end]

                recent_revenue = sum(e.attributed_value for e in recent_ledger)
                prev_revenue = sum(e.attributed_value for e in prev_ledger)
                revenue_growth = ((recent_revenue - prev_revenue) / prev_revenue) if prev_revenue > 0 else 0

                win_rate = calculate_win_rate(
                    selected_partner_id,
                    st.session_state.targets,
                    st.session_state.touchpoints
                )

                avg_deal = sum(e.attributed_value for e in partner_ledger) / len(partner_ledger) if partner_ledger else 0

                deal_velocity = calculate_deal_velocity(
                    selected_partner_id,
                    st.session_state.targets,
                    st.session_state.touchpoints
                )

                metrics_dict = {
                    "revenue_growth": revenue_growth * 100,
                    "win_rate": win_rate,
                    "avg_deal_size": avg_deal,
                    "deal_velocity": deal_velocity
                }

                insights = generate_partner_insights(selected_partner_id, health_score, metrics_dict)

                # Strengths
                if insights.strengths:
                    st.markdown("**✅ Strengths:**")
                    for strength in insights.strengths[:3]:
                        st.markdown(f"• {strength}")

                # Improvements
                if insights.improvements:
                    st.markdown("**⚠️ Areas to Improve:**")
                    for improvement in insights.improvements[:2]:
                        st.markdown(f"• {improvement}")

                # Recommendations
                if insights.recommendations:
                    st.markdown("**💡 Recommendations:**")
                    for rec in insights.recommendations[:2]:
                        st.markdown(f"• {rec}")

        except Exception as e:
            st.error(f"Error calculating health score: {str(e)}")
            health_score = None

        st.markdown("---")

        # Key Metrics Row
        st.markdown("### Key Metrics")
        metric_cols = st.columns(5)

        partner_ledger = [e for e in st.session_state.ledger if e.partner_id == selected_partner_id]
        total_attributed = sum(e.attributed_value for e in partner_ledger)
        deal_count = len(set(e.target_id for e in partner_ledger))
        avg_deal_size = total_attributed / deal_count if deal_count > 0 else 0

        win_rate_calc = calculate_win_rate(
            selected_partner_id,
            st.session_state.targets,
            st.session_state.touchpoints
        )

        with metric_cols[0]:
            st.metric("Total Attributed", format_currency_compact(total_attributed))

        with metric_cols[1]:
            st.metric("Deals Influenced", str(deal_count))

        with metric_cols[2]:
            st.metric("Avg Deal Size", format_currency_compact(avg_deal_size))

        with metric_cols[3]:
            if win_rate_calc is not None:
                st.metric("Win Rate", f"{win_rate_calc:.0%}")
            else:
                st.metric("Win Rate", "N/A", help="No stage data available")

        with metric_cols[4]:
            partner_tps_recent = [tp for tp in st.session_state.touchpoints
                                 if tp.partner_id == selected_partner_id and tp.timestamp]
            if partner_tps_recent:
                last_tp = max(partner_tps_recent, key=lambda tp: tp.timestamp)
                st.metric("Last Activity", format_days_ago(last_tp.timestamp))
            else:
                st.metric("Last Activity", "N/A")

        st.markdown("---")

        # Performance Trends
        st.markdown("### Performance Trends")
        trend_col1, trend_col2 = st.columns(2)

        with trend_col1:
            # Revenue trend (12 months)
            try:
                # Calculate monthly revenue for this partner
                monthly_data = {}
                for entry in partner_ledger:
                    month_key = entry.calculation_timestamp.strftime("%Y-%m")
                    monthly_data[month_key] = monthly_data.get(month_key, 0) + entry.attributed_value

                if monthly_data:
                    # Get last 12 months
                    months = sorted(monthly_data.keys())[-12:]
                    trend_df = pd.DataFrame({
                        'month': months,
                        'revenue': [monthly_data[m] for m in months]
                    })

                    fig = create_partner_revenue_trend(selected_partner_name, trend_df)
                    st.plotly_chart(fig, use_container_width=True, key="mgmt_revenue_trend")
                else:
                    st.info("No revenue history available")
            except Exception as e:
                st.warning(f"Unable to create revenue trend: {str(e)}")

        with trend_col2:
            # Activity trend
            try:
                # Calculate monthly touchpoints
                monthly_tps = {}
                for tp in partner_tps_recent:
                    if tp.timestamp:
                        month_key = tp.timestamp.strftime("%Y-%m")
                        monthly_tps[month_key] = monthly_tps.get(month_key, 0) + 1

                if monthly_tps:
                    months = sorted(monthly_tps.keys())[-12:]
                    activity_df = pd.DataFrame({
                        'month': months,
                        'touchpoints': [monthly_tps[m] for m in months]
                    })

                    fig = create_partner_activity_trend(selected_partner_name, activity_df)
                    st.plotly_chart(fig, use_container_width=True, key="mgmt_activity_trend")
                else:
                    st.info("No activity history available")
            except Exception as e:
                st.warning(f"Unable to create activity trend: {str(e)}")

        st.markdown("---")

        # Recent Deals Table
        st.markdown("### Recent Deals (Last 10)")

        partner_target_ids = {tp.target_id for tp in st.session_state.touchpoints
                              if tp.partner_id == selected_partner_id}

        recent_deals = []
        for target in st.session_state.targets:
            if target.id in partner_target_ids:
                # Get this partner's ledger entry for this target
                entry = next((e for e in partner_ledger if e.target_id == target.id), None)

                if entry:
                    # Get role from touchpoint
                    tp = next((t for t in st.session_state.touchpoints
                             if t.target_id == target.id and t.partner_id == selected_partner_id), None)

                    recent_deals.append({
                        "Deal ID": target.external_id,
                        "Account": target.metadata.get("account_name", "Unknown"),
                        "Close Date": target.timestamp.strftime("%Y-%m-%d"),
                        "Value": format_currency_compact(target.value),
                        "Role": tp.role if tp else "N/A",
                        "Attribution": f"{entry.split_percentage:.0%}",
                        "Attributed $": format_currency_compact(entry.attributed_value)
                    })

        if recent_deals:
            # Sort by close date descending
            recent_deals_sorted = sorted(recent_deals, key=lambda d: d["Close Date"], reverse=True)[:10]
            st.dataframe(
                pd.DataFrame(recent_deals_sorted),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No deals found for this partner")


# ============================================================================
# TAB 4: DATA IMPORT
# ============================================================================

with tabs[4]:
    st.title("📥 Data Import")
    st.caption("Upload CSV data with automatic schema detection")

    # ========================================
    # DEMO DATA PLAYGROUND
    # ========================================
    st.markdown("### 🎲 Quick Start - Load Demo Data")

    demo_col1, demo_col2 = st.columns([2, 1])

    with demo_col1:
        st.info("""
**Never demo an empty app!** Load realistic SaaS B2B sample data:
- 10 opportunities ($10K-$2M range)
- 25 partner touchpoints (7 partners across SI, Influence, Referral, ISV roles)
- 3 pre-configured attribution rules
- Pre-calculated ledger entries

Perfect for exploring features and presenting to stakeholders.
        """)

    with demo_col2:
        if st.button("🚀 Load Demo Data", type="primary", use_container_width=True):
            with st.spinner("Generating demo dataset..."):
                # Generate demo data
                demo_targets, demo_touchpoints, demo_rules, demo_ledger = generate_complete_demo_data()

                # Clear existing data
                st.session_state.targets = demo_targets
                st.session_state.touchpoints = demo_touchpoints
                st.session_state.rules = demo_rules
                st.session_state.ledger = demo_ledger

                # Update partners dictionary
                st.session_state.partners = DEMO_PARTNER_NAMES.copy()

                # Get summary
                summary = get_demo_data_summary(demo_targets, demo_touchpoints, demo_rules, demo_ledger)

                st.success("✅ **Demo Data Loaded!**")
                st.markdown(f"""
**Dataset Summary:**
- 📊 {summary['num_targets']} opportunities
- 🤝 {summary['num_touchpoints']} partner touchpoints
- ⚙️ {summary['num_rules']} attribution rules
- 📝 {summary['num_ledger_entries']} ledger entries

**💰 Revenue:** ${summary['total_revenue']:,.2f} total, ${summary['total_attributed']:,.2f} attributed ({summary['attribution_accuracy']:.1f}% coverage)

**📅 Date Range:** {summary['date_range'][0]} to {summary['date_range'][1]}

**🏆 Top 3 Partners:**
                """)
                for idx, (partner_name, revenue) in enumerate(summary['top_partners'][:3], 1):
                    st.markdown(f"{idx}. **{partner_name}**: ${revenue:,.2f}")

                st.info("👉 Go to the **Dashboard** tab to see visualizations or **Ledger Explorer** to see attribution results!")

    st.markdown("---")
    st.markdown("### 📂 Or Import Your Own Data")

    import_tabs = st.tabs(["Upload CSV", "Download Templates", "Manual Entry"])

    # Upload CSV sub-tab
    with import_tabs[0]:
        st.markdown("### Upload CSV File")
        st.info("""
**Supported formats:**
- Salesforce Opportunity exports
- HubSpot Deal exports
- Custom CSV with opportunity/partner data

**Auto-detection:** We'll infer your schema automatically!
        """)

        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            help="Upload Salesforce/HubSpot export or custom CSV"
        )

        if uploaded_file:
            # Read and preview
            csv_content = uploaded_file.read()
            preview_df = pd.read_csv(pd.io.common.BytesIO(csv_content))

            st.markdown("#### Preview (First 5 Rows)")
            st.dataframe(preview_df.head(), use_container_width=True)

            # Ingest
            if st.button("Import Data"):
                with st.spinner("Ingesting data..."):
                    result = ingest_csv(csv_content)

                    st.success(f"✅ **Import Complete!**")
                    st.markdown(f"""
**Targets loaded:** {result['stats']['targets_loaded']}
**Touchpoints loaded:** {result['stats']['touchpoints_loaded']}
**Confidence:** {result['schema']['confidence']:.0%}
                    """)

                    # Add to session state
                    # Assign IDs to targets
                    next_target_id = max([t.id for t in st.session_state.targets], default=0) + 1
                    for idx, target in enumerate(result["targets"]):
                        target.id = next_target_id + idx
                        st.session_state.targets.append(target)

                    # Update touchpoints with correct target IDs
                    target_lookup = {t.external_id: t.id for t in result["targets"]}
                    next_tp_id = max([tp.id for tp in st.session_state.touchpoints], default=0) + 1

                    for idx, tp in enumerate(result["touchpoints"]):
                        tp.id = next_tp_id + idx
                        # Update target_id from temporary index to actual ID
                        if tp.target_id < len(result["targets"]):
                            external_id = result["targets"][tp.target_id].external_id
                            tp.target_id = target_lookup[external_id]
                        st.session_state.touchpoints.append(tp)

                    # Extract partner IDs
                    for tp in result["touchpoints"]:
                        if tp.partner_id not in st.session_state.partners:
                            st.session_state.partners[tp.partner_id] = tp.partner_id  # Use ID as name for now

                    # Show warnings
                    if result["validation_errors"]:
                        with st.expander("⚠️ Warnings & Validation Issues"):
                            for error in result["validation_errors"]:
                                st.warning(error)

                    st.rerun()

    # Download Templates sub-tab
    with import_tabs[1]:
        st.markdown("### Download CSV Templates")

        template_cols = st.columns(3)

        with template_cols[0]:
            st.markdown("**Salesforce Format**")
            st.download_button(
                "Download Salesforce Template",
                data=generate_csv_template("salesforce"),
                file_name="salesforce_template.csv",
                mime="text/csv",
                use_container_width=True
            )

        with template_cols[1]:
            st.markdown("**HubSpot Format**")
            st.download_button(
                "Download HubSpot Template",
                data=generate_csv_template("hubspot"),
                file_name="hubspot_template.csv",
                mime="text/csv",
                use_container_width=True
            )

        with template_cols[2]:
            st.markdown("**Minimal Format**")
            st.download_button(
                "Download Minimal Template",
                data=generate_csv_template("minimal"),
                file_name="minimal_template.csv",
                mime="text/csv",
                use_container_width=True
            )

    # Manual Entry sub-tab
    with import_tabs[2]:
        st.markdown("### Manual Data Entry")
        st.info("Quick way to add a single target + touchpoint for testing")

        with st.form("manual_entry"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Target (Opportunity)**")
                target_id = st.text_input("External ID", value=f"T{len(st.session_state.targets)+1}")
                target_value = st.number_input("Value ($)", min_value=0.0, value=100000.0)
                target_date = st.date_input("Close Date", value=date.today())

            with col2:
                st.markdown("**Partner Touchpoint**")
                partner_id = st.text_input("Partner ID", value=f"P{len(st.session_state.partners)+1:03d}")
                partner_name = st.text_input("Partner Name", value="New Partner")
                partner_role = st.selectbox("Role", DEFAULT_PARTNER_ROLES)

            if st.form_submit_button("Add Entry"):
                # Create target
                new_target = AttributionTarget(
                    id=len(st.session_state.targets) + 1,
                    type=TargetType.OPPORTUNITY,
                    external_id=target_id,
                    value=target_value,
                    timestamp=datetime.combine(target_date, datetime.min.time()),
                    metadata={"source": "manual_entry"}
                )
                st.session_state.targets.append(new_target)

                # Create touchpoint
                new_touchpoint = PartnerTouchpoint(
                    id=len(st.session_state.touchpoints) + 1,
                    partner_id=partner_id,
                    target_id=new_target.id,
                    touchpoint_type=TouchpointType.MANUAL_OVERRIDE,
                    role=partner_role,
                    timestamp=datetime.combine(target_date, datetime.min.time())
                )
                st.session_state.touchpoints.append(new_touchpoint)

                # Add partner
                if partner_id not in st.session_state.partners:
                    st.session_state.partners[partner_id] = partner_name

                st.success(f"✅ Added target {target_id} with partner {partner_name}")
                st.rerun()


# ============================================================================
# ============================================================================
# TAB 5: VISUAL RULE BUILDER (SIMPLIFIED UX)
# ============================================================================

with tabs[5]:
    st.title("🎨 Build Your Attribution Rule")
    st.caption("No coding required - just drag sliders and see results instantly")

    # Quick start templates
    st.markdown("### 🚀 Quick Start")
    st.markdown("Pick a template or build from scratch:")

    template_cols = st.columns(4)

    template_selected = None
    with template_cols[0]:
        if st.button("⚡ Equal Split\n*All partners get equal credit*", use_container_width=True, key="tmpl_equal"):
            template_selected = "equal"

    with template_cols[1]:
        if st.button("🎯 60/30/10 Split\n*SI 60%, Influence 30%, Referral 10%*", use_container_width=True, key="tmpl_603010"):
            template_selected = "603010"

    with template_cols[2]:
        if st.button("🏆 Winner Takes All\n*First partner gets 100%*", use_container_width=True, key="tmpl_winner"):
            template_selected = "winner"

    with template_cols[3]:
        if st.button("🔨 Custom\n*Build your own rule*", use_container_width=True, key="tmpl_custom"):
            template_selected = "custom"

    st.markdown("---")

    # Initialize session state for rule builder
    if "visual_builder" not in st.session_state:
        st.session_state.visual_builder = {
            "rule_name": "My Custom Rule",
            "roles": ["Implementation (SI)", "Referral"],
            "splits": {"Implementation (SI)": 70, "Referral": 30},
            "applies_to_all": True,
            "min_deal_size": 0
        }

    # Apply template if selected
    if template_selected == "equal":
        st.session_state.visual_builder["rule_name"] = "Equal Split"
        st.session_state.visual_builder["splits"] = {
            role: 100 // len(DEFAULT_PARTNER_ROLES)
            for role in DEFAULT_PARTNER_ROLES[:3]
        }
        st.session_state.visual_builder["roles"] = DEFAULT_PARTNER_ROLES[:3]

    elif template_selected == "603010":
        st.session_state.visual_builder["rule_name"] = "60/30/10 Split"
        st.session_state.visual_builder["splits"] = {
            "Implementation (SI)": 60,
            "Influence": 30,
            "Referral": 10
        }
        st.session_state.visual_builder["roles"] = ["Implementation (SI)", "Influence", "Referral"]

    elif template_selected == "winner":
        st.session_state.visual_builder["rule_name"] = "Winner Takes All"
        st.session_state.visual_builder["splits"] = {"First Touch": 100}
        st.session_state.visual_builder["roles"] = ["First Touch"]

    # Step 1: Which deals does this apply to?
    st.markdown("### 1️⃣ Which deals should use this rule?")

    col1, col2 = st.columns(2)

    with col1:
        applies_to = st.radio(
            "",
            ["All deals", "Deals over a certain size", "Specific products"],
            key="applies_to_radio",
            horizontal=False
        )

        st.session_state.visual_builder["applies_to_all"] = (applies_to == "All deals")

    with col2:
        if applies_to == "Deals over a certain size":
            min_size = st.slider(
                "Minimum deal value",
                min_value=0,
                max_value=500000,
                value=100000,
                step=10000,
                format="$%d",
                key="min_deal_slider"
            )
            st.session_state.visual_builder["min_deal_size"] = min_size
            st.info(f"This rule applies to deals worth **${min_size:,}** or more")
        elif applies_to == "Specific products":
            product_filter = st.text_input(
                "Product/Service",
                placeholder="e.g., Enterprise Plan, Professional Services",
                key="product_filter"
            )

    st.markdown("---")

    # Step 2: Build the split
    st.markdown("### 2️⃣ How should we split credit among partners?")

    # Role selection
    st.markdown("**Select partner roles:**")
    selected_roles = st.multiselect(
        "",
        options=DEFAULT_PARTNER_ROLES,
        default=st.session_state.visual_builder.get("roles", ["Implementation (SI)", "Referral"]),
        key="role_multiselect",
        help="Choose which partner roles should get credit"
    )

    if len(selected_roles) == 0:
        st.warning("⚠️ Please select at least one partner role")
        st.stop()

    st.session_state.visual_builder["roles"] = selected_roles

    st.markdown("**Adjust credit split:**")

    # Visual sliders for each role
    splits = {}
    total_allocated = 0

    for role in selected_roles:
        # Get previous value or default
        default_value = st.session_state.visual_builder["splits"].get(role, 100 // len(selected_roles))

        col1, col2 = st.columns([3, 1])

        with col1:
            split_pct = st.slider(
                f"{role}",
                min_value=0,
                max_value=100,
                value=int(default_value),
                step=5,
                key=f"split_{role}",
                help=f"Percentage of deal value attributed to {role}"
            )

        with col2:
            st.metric("", f"{split_pct}%", label_visibility="collapsed")

        splits[role] = split_pct
        total_allocated += split_pct

    st.session_state.visual_builder["splits"] = splits

    # Validation
    st.markdown("---")

    if total_allocated != 100:
        st.error(f"❌ **Total is {total_allocated}%** (must equal 100%)")
        st.markdown("Adjust the sliders above so they add up to 100%")
    else:
        st.success(f"✅ **Perfect!** Splits add up to 100%")

    # Step 3: Live Preview
    st.markdown("---")
    st.markdown("### 3️⃣ Preview")

    # Example deal preview
    st.markdown("**Example: $100,000 Deal**")

    preview_data = []
    for role, pct in splits.items():
        amount = 100000 * (pct / 100)
        preview_data.append({
            "Partner Role": role,
            "Split": f"{pct}%",
            "Amount": f"${amount:,.0f}"
        })

    # Show as a nice table
    import pandas as pd
    preview_df = pd.DataFrame(preview_data)
    st.dataframe(preview_df, use_container_width=True, hide_index=True)

    # Visual bar chart
    import plotly.graph_objects as go

    fig = go.Figure(data=[
        go.Bar(
            x=list(splits.values()),
            y=list(splits.keys()),
            orientation='h',
            text=[f"{v}%" for v in splits.values()],
            textposition='inside',
            marker=dict(
                color=['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b'][:len(splits)]
            )
        )
    ])

    fig.update_layout(
        title="Credit Split Visualization",
        xaxis_title="Percentage (%)",
        yaxis_title="Partner Role",
        height=300,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Step 4: Save
    st.markdown("---")
    st.markdown("### 4️⃣ Save Your Rule")

    col1, col2 = st.columns([2, 1])

    with col1:
        rule_name = st.text_input(
            "Rule Name",
            value=st.session_state.visual_builder.get("rule_name", "My Custom Rule"),
            placeholder="e.g., '60/30/10 Enterprise Split'",
            key="rule_name_input"
        )

    with col2:
        st.markdown("")  # Spacing
        st.markdown("")

        if total_allocated == 100 and rule_name:
            if st.button("💾 Save Rule", type="primary", use_container_width=True, key="save_visual_rule"):
                # Create the rule
                new_rule = AttributionRule(
                    id=len(st.session_state.rules) + 1,
                    name=rule_name,
                    model_type=AttributionModel.ROLE_WEIGHTED,
                    config={"weights": {role: pct/100 for role, pct in splits.items()}},
                    split_constraint=SplitConstraint.MUST_SUM_TO_100,
                    applies_to={
                        "min_value": st.session_state.visual_builder.get("min_deal_size", 0)
                    } if not st.session_state.visual_builder.get("applies_to_all", True) else {},
                    priority=100,
                    active=True
                )

                st.session_state.rules.append(new_rule)

                # Recalculate attribution
                with st.spinner("💡 Applying your new rule..."):
                    count = calculate_attribution_for_all_targets()

                st.success(f"✅ Rule '{rule_name}' saved! Created {count} ledger entries")
                st.balloons()

                # Reset builder
                st.session_state.visual_builder = {
                    "rule_name": "My Custom Rule",
                    "roles": ["Implementation (SI)", "Referral"],
                    "splits": {"Implementation (SI)": 70, "Referral": 30},
                    "applies_to_all": True,
                    "min_deal_size": 0
                }

                st.rerun()
        else:
            st.button("💾 Save Rule", type="primary", use_container_width=True, disabled=True, key="save_visual_rule_disabled")
            if total_allocated != 100:
                st.caption("⚠️ Fix the split percentages first")
            elif not rule_name:
                st.caption("⚠️ Enter a rule name first")

    # Advanced: Natural Language Option
    with st.expander("💬 Or describe your rule in plain English (Advanced)", expanded=False):
        st.markdown("**Describe your attribution model:**")
        nl_input = st.text_area(
            "",
            placeholder="e.g., 'Give 70% to SI partners and 30% to referral partners for enterprise deals'",
            height=100,
            key="nl_advanced"
        )

        if st.button("🚀 Generate from Description", key="nl_generate"):
            if nl_input:
                st.info("💡 Natural language parsing coming soon! For now, use the visual builder above.")
            else:
                st.warning("Please enter a description first")
# ============================================================================
# TAB 6: RULES & TEMPLATES
# ============================================================================

with tabs[6]:
    st.title("📋 Active Rules & Templates")

    if st.session_state.rules:
        st.markdown(f"### Active Rules ({len(st.session_state.rules)})")

        for rule in st.session_state.rules:
            with st.expander(f"{'✅' if rule.active else '❌'} {rule.name} ({rule.model_type.value})"):
                st.markdown(f"**Priority:** {rule.priority}")
                st.markdown(f"**Split Constraint:** {rule.split_constraint.value}")
                st.json(rule.config)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"{'Deactivate' if rule.active else 'Activate'}", key=f"toggle_{rule.id}"):
                        rule.active = not rule.active
                        st.rerun()

                with col2:
                    if st.button("Delete", key=f"delete_{rule.id}"):
                        st.session_state.rules = [r for r in st.session_state.rules if r.id != rule.id]
                        st.rerun()
    else:
        st.info("No rules created yet. Use the Rule Builder tab to create your first rule!")


# ============================================================================
# TAB 7: MEASUREMENT WORKFLOWS
# ============================================================================

with tabs[7]:
    st.title("🔄 Measurement Workflows")
    st.caption("Configure how your company measures partner contribution")

    st.markdown("""
    **Measurement Workflows** define which data sources you use to track partner impact.
    Different companies measure partners differently - configure your approach here.

    **Common workflows:**
    - Deal Registration Primary: Use deal reg if exists, else touchpoints
    - Marketplace Only: 100% to marketplace partner
    - CRM Field with Fallback: Use Partner field if set, else calculate from activities
    - Hybrid SI + Influence: 80% to deal reg, 20% to influence touchpoints
    """)

    # Initialize workflows in session state
    if "workflows" not in st.session_state:
        st.session_state.workflows = []

    # Show existing workflows
    if st.session_state.workflows:
        st.markdown("### 📋 Your Workflows")

        for workflow in st.session_state.workflows:
            with st.expander(f"{'⭐ PRIMARY' if workflow.is_primary else '🔧'} {workflow.name}", expanded=False):
                st.markdown(f"**Description:** {workflow.description}")

                # Data sources
                st.markdown("**Data Sources (Priority Order):**")
                sorted_sources = sorted(workflow.data_sources, key=lambda x: x.priority)
                for i, ds in enumerate(sorted_sources):
                    status = "✅ Enabled" if ds.enabled else "❌ Disabled"
                    st.markdown(f"{i+1}. **{ds.source_type.value}** - Priority {ds.priority} - {status}")
                    if ds.config:
                        st.json(ds.config)

                # Conflict resolution
                st.markdown(f"**Conflict Resolution:** {workflow.conflict_resolution}")
                st.markdown(f"**Fallback Strategy:** {workflow.fallback_strategy}")

                # Actions
                col1, col2, col3 = st.columns(3)
                with col1:
                    if not workflow.is_primary and st.button(f"Set as Primary", key=f"primary_{workflow.id}"):
                        # Mark this as primary, unmark others
                        for w in st.session_state.workflows:
                            w.is_primary = (w.id == workflow.id)
                        st.success(f"✅ Set {workflow.name} as primary workflow")
                        st.rerun()

                with col2:
                    if st.button(f"{'Disable' if workflow.active else 'Enable'}", key=f"toggle_{workflow.id}"):
                        workflow.active = not workflow.active
                        st.rerun()

                with col3:
                    if st.button(f"Delete", key=f"del_workflow_{workflow.id}", type="secondary"):
                        st.session_state.workflows.remove(workflow)
                        st.success(f"🗑️ Deleted {workflow.name}")
                        st.rerun()

    else:
        st.info("No workflows configured yet. Create one from a template below.")

    # Workflow Templates
    st.markdown("### 📚 Create from Template")

    template_option = st.selectbox(
        "Select Template",
        [
            "Deal Registration Primary",
            "Marketplace Only",
            "CRM Field with Fallback",
            "Hybrid SI + Influence (80/20)",
            "Touchpoint Tracking Only (Default)"
        ],
        help="Choose a pre-configured workflow template"
    )

    # Template descriptions
    template_descriptions = {
        "Deal Registration Primary": "Use partner-submitted deal regs if they exist, otherwise fall back to touchpoint tracking",
        "Marketplace Only": "100% attribution to marketplace partner for marketplace transactions",
        "CRM Field with Fallback": "Use the CRM Partner field if populated, otherwise calculate from touchpoints",
        "Hybrid SI + Influence (80/20)": "80% credit to deal reg partner, 20% to influence touchpoints",
        "Touchpoint Tracking Only (Default)": "Traditional activity-based tracking (meetings, emails, etc.)"
    }

    st.info(f"ℹ️ {template_descriptions[template_option]}")

    if st.button("Create Workflow from Template", type="primary"):
        from models_new import MeasurementWorkflow, DataSourceConfig, DataSource
        from datetime import datetime

        # Generate workflow ID
        workflow_id = len(st.session_state.workflows) + 1

        # Create workflow based on template
        if template_option == "Deal Registration Primary":
            workflow = MeasurementWorkflow(
                id=workflow_id,
                company_id="demo_company",
                name="Deal Registration Primary",
                description="Use deal reg if exists, else touchpoint tracking",
                data_sources=[
                    DataSourceConfig(
                        source_type=DataSource.DEAL_REGISTRATION,
                        enabled=True,
                        priority=1,
                        requires_validation=True,
                        config={"require_approval": True, "expiry_days": 90}
                    ),
                    DataSourceConfig(
                        source_type=DataSource.TOUCHPOINT_TRACKING,
                        enabled=True,
                        priority=2,
                        config={}
                    )
                ],
                conflict_resolution="priority",
                fallback_strategy="next_priority",
                is_primary=len(st.session_state.workflows) == 0,  # First workflow is primary
                active=True,
                created_at=datetime.now()
            )

        elif template_option == "Marketplace Only":
            workflow = MeasurementWorkflow(
                id=workflow_id,
                company_id="demo_company",
                name="Marketplace Only",
                description="100% attribution to marketplace partner",
                data_sources=[
                    DataSourceConfig(
                        source_type=DataSource.MARKETPLACE_TRANSACTIONS,
                        enabled=True,
                        priority=1,
                        config={"platform": "aws"}
                    )
                ],
                conflict_resolution="priority",
                fallback_strategy="manual",
                applies_to={"metadata.source": "marketplace"},
                is_primary=False,
                active=True,
                created_at=datetime.now()
            )

        elif template_option == "CRM Field with Fallback":
            workflow = MeasurementWorkflow(
                id=workflow_id,
                company_id="demo_company",
                name="CRM Partner Field with Fallback",
                description="Use Partner__c if set, else calculate from touchpoints",
                data_sources=[
                    DataSourceConfig(
                        source_type=DataSource.CRM_OPPORTUNITY_FIELD,
                        enabled=True,
                        priority=1,
                        config={"field_name": "Partner__c", "role_field": "Partner_Role__c"}
                    ),
                    DataSourceConfig(
                        source_type=DataSource.TOUCHPOINT_TRACKING,
                        enabled=True,
                        priority=2,
                        config={}
                    )
                ],
                conflict_resolution="priority",
                fallback_strategy="next_priority",
                is_primary=len(st.session_state.workflows) == 0,
                active=True,
                created_at=datetime.now()
            )

        elif template_option == "Hybrid SI + Influence (80/20)":
            workflow = MeasurementWorkflow(
                id=workflow_id,
                company_id="demo_company",
                name="Hybrid Deal Reg + Influence",
                description="80% to deal reg partner, 20% to influence touchpoints",
                data_sources=[
                    DataSourceConfig(
                        source_type=DataSource.DEAL_REGISTRATION,
                        enabled=True,
                        priority=1,
                        config={"attribution_weight": 0.8, "require_approval": True}
                    ),
                    DataSourceConfig(
                        source_type=DataSource.TOUCHPOINT_TRACKING,
                        enabled=True,
                        priority=2,
                        config={"attribution_weight": 0.2}
                    )
                ],
                conflict_resolution="merge",  # Combine both sources
                fallback_strategy="next_priority",
                is_primary=len(st.session_state.workflows) == 0,
                active=True,
                created_at=datetime.now()
            )

        else:  # Touchpoint Tracking Only
            workflow = MeasurementWorkflow(
                id=workflow_id,
                company_id="demo_company",
                name="Touchpoint Tracking (Default)",
                description="Traditional activity-based tracking",
                data_sources=[
                    DataSourceConfig(
                        source_type=DataSource.TOUCHPOINT_TRACKING,
                        enabled=True,
                        priority=1,
                        config={}
                    )
                ],
                conflict_resolution="priority",
                fallback_strategy="equal_split",
                is_primary=len(st.session_state.workflows) == 0,
                active=True,
                created_at=datetime.now()
            )

        st.session_state.workflows.append(workflow)
        st.success(f"✅ Created workflow: {workflow.name}")
        st.rerun()

    # Data Source Upload
    st.markdown("---")
    st.markdown("### 📥 Upload Data from Different Sources")

    upload_source_type = st.selectbox(
        "Data Source Type",
        [
            "Touchpoint Tracking (CSV)",
            "Deal Registrations (CSV)",
            "CRM Partner Field Export (CSV)",
            "Marketplace Transactions (JSON)"
        ],
        help="Select the type of data you want to upload"
    )

    if upload_source_type == "Deal Registrations (CSV)":
        st.markdown("""
        **Deal Registration CSV Format:**
        - `deal_reg_id`: Unique deal registration ID
        - `partner_id`: Partner identifier
        - `opportunity_id`: Your internal opportunity ID
        - `submitted_date`: When partner submitted (YYYY-MM-DD)
        - `status`: pending/approved/rejected/expired (optional, defaults to pending)
        - `partner_role`: Partner's role (optional, defaults to Referral)
        """)

        uploaded_file = st.file_uploader("Upload Deal Registrations CSV", type="csv", key="deal_reg_upload")

        if uploaded_file:
            if st.button("Process Deal Registrations"):
                from data_ingestion import DataSourceIngestion

                ingestion = DataSourceIngestion()

                # Get primary workflow for validation rules
                primary_workflow = next((w for w in st.session_state.workflows if w.is_primary), None)

                # Create target mapping
                target_mapping = {t.external_id: t.id for t in st.session_state.targets}

                result = ingestion.ingest_deal_registrations(
                    csv_content=uploaded_file.getvalue(),
                    workflow=primary_workflow,
                    target_id_mapping=target_mapping
                )

                # Add touchpoints to session state
                st.session_state.touchpoints.extend(result["touchpoints"])

                st.success(f"✅ Created {result['count']} deal registration touchpoints")

                if result["warnings"]:
                    st.warning(f"⚠️ {len(result['warnings'])} warnings:")
                    for warning in result["warnings"][:5]:
                        st.text(f"  • {warning}")

                # Show stats
                st.json(result["stats"])

    elif upload_source_type == "CRM Partner Field Export (CSV)":
        st.markdown("""
        **CRM Export CSV Format:**
        - `id`: Opportunity ID
        - `created_date`: Opportunity created date
        - `Partner__c`: Partner field value
        - `Partner_Role__c`: Partner role field (optional)
        - Other fields will be stored in metadata
        """)

        uploaded_file = st.file_uploader("Upload CRM Export CSV", type="csv", key="crm_upload")

        if uploaded_file:
            st.info("CRM partner field import coming soon!")

    else:
        st.info(f"{upload_source_type} import interface coming soon!")


# ============================================================================
# TAB 3: DEAL DRILLDOWN
# ============================================================================

with tabs[3]:
    col_title, col_export = st.columns([4, 1])

    with col_title:
        st.title("💰 Deal Drilldown")
        st.caption("Detailed attribution breakdown for individual deals - perfect for partner dispute resolution")

    with col_export:
        st.markdown("") # Spacing
        if st.button("📥 Export CSV", key="deal_export", use_container_width=True):
            filtered_ledger = apply_global_filters(st.session_state.ledger)
            csv_data = export_ledger_to_csv(filtered_ledger)
            st.download_button(
                "Download Data",
                csv_data,
                "deal_drilldown.csv",
                "text/csv",
                key="deal_download"
            )

    st.markdown("---")

    if not st.session_state.targets:
        st.info("No deals available. Load data first in the Data Import tab.")
    else:
        # Deal Selector
        st.markdown("### Select Deal to Analyze")

        deal_options = {}
        for target in st.session_state.targets:
            account_name = target.metadata.get('account_name', 'Unknown Account')
            deal_label = f"{target.external_id} - {account_name} (${target.value:,.0f})"
            deal_options[deal_label] = target.id

        selected_deal_label = st.selectbox(
            "Choose Deal",
            options=list(deal_options.keys()),
            help="Select a deal to see its full attribution breakdown"
        )

        selected_target_id = deal_options[selected_deal_label]
        selected_target = next(t for t in st.session_state.targets if t.id == selected_target_id)

        # Deal Summary Card
        st.markdown("---")
        st.markdown("### Deal Information")

        deal_col1, deal_col2, deal_col3, deal_col4 = st.columns(4)

        with deal_col1:
            st.metric("Deal Value", f"${selected_target.value:,.0f}")

        with deal_col2:
            account_name = selected_target.metadata.get('account_name', 'Unknown')
            st.metric("Account", account_name)

        with deal_col3:
            close_date = selected_target.timestamp.strftime("%Y-%m-%d") if selected_target.timestamp else "N/A"
            st.metric("Close Date", close_date)

        with deal_col4:
            region = selected_target.metadata.get('region', 'N/A')
            st.metric("Region", region)

        # Partner Touchpoints
        st.markdown("---")
        st.markdown("### Partner Engagement History")

        deal_touchpoints = [tp for tp in st.session_state.touchpoints if tp.target_id == selected_target_id]

        if deal_touchpoints:
            touchpoint_data = []
            for tp in sorted(deal_touchpoints, key=lambda x: x.timestamp or datetime.min):
                partner_name = st.session_state.partners.get(tp.partner_id, tp.partner_id)
                touchpoint_data.append({
                    "Partner": partner_name,
                    "Role": tp.role,
                    "Date": tp.timestamp.strftime("%Y-%m-%d") if tp.timestamp else "N/A",
                    "Activity Weight": f"{tp.weight:.0f}",
                    "Days Before Close": (selected_target.timestamp - tp.timestamp).days if (selected_target.timestamp and tp.timestamp) else "N/A"
                })

            st.dataframe(pd.DataFrame(touchpoint_data), use_container_width=True, hide_index=True)
        else:
            st.warning("No partner touchpoints recorded for this deal.")

        # Attribution Breakdown
        st.markdown("---")
        st.markdown("### Attribution Calculation Breakdown")

        deal_ledger = [entry for entry in st.session_state.ledger if entry.target_id == selected_target_id]

        if deal_ledger:
            # Summary metrics
            total_attributed = sum(entry.attributed_value for entry in deal_ledger)
            attribution_coverage = (total_attributed / selected_target.value * 100) if selected_target.value > 0 else 0

            summary_col1, summary_col2, summary_col3 = st.columns(3)

            with summary_col1:
                st.metric("Total Attributed", f"${total_attributed:,.2f}", help="Sum of all partner attribution for this deal")

            with summary_col2:
                st.metric("Coverage", f"{attribution_coverage:.1f}%", help="Percentage of deal value attributed to partners")

            with summary_col3:
                st.metric("Partners Credited", len(deal_ledger), help="Number of partners receiving attribution")

            # Detailed Attribution Table
            st.markdown("#### Partner-by-Partner Breakdown")

            attribution_data = []
            for entry in sorted(deal_ledger, key=lambda e: e.attributed_value, reverse=True):
                partner_name = st.session_state.partners.get(entry.partner_id, entry.partner_id)
                rule = next((r for r in st.session_state.rules if r.id == entry.rule_id), None)
                rule_name = rule.name if rule else f"Rule #{entry.rule_id}"

                # Get touchpoint details for this partner
                partner_tps = [tp for tp in deal_touchpoints if tp.partner_id == entry.partner_id]
                num_touchpoints = len(partner_tps)
                roles = ", ".join(set(tp.role for tp in partner_tps)) if partner_tps else "N/A"

                attribution_data.append({
                    "Partner": partner_name,
                    "Role(s)": roles,
                    "Touchpoints": num_touchpoints,
                    "Attribution %": f"{entry.split_percentage:.1%}",
                    "Attributed $": f"${entry.attributed_value:,.2f}",
                    "Rule Applied": rule_name,
                    "Calculated": entry.calculation_timestamp.strftime("%Y-%m-%d %H:%M")
                })

            st.dataframe(pd.DataFrame(attribution_data), use_container_width=True, hide_index=True)

            # Visualization
            st.markdown("#### Attribution Split Visualization")

            attribution_chart_df = pd.DataFrame([
                {"Partner": st.session_state.partners.get(entry.partner_id, entry.partner_id),
                 "Value": entry.attributed_value}
                for entry in deal_ledger
            ])

            import plotly.express as px
            fig = px.pie(
                attribution_chart_df,
                values='Value',
                names='Partner',
                title=f"Attribution Split - {selected_target.external_id}",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)

            # Audit Trail
            with st.expander("🔍 View Detailed Audit Trail"):
                st.markdown("**Calculation Logic:**")
                for entry in deal_ledger:
                    rule = next((r for r in st.session_state.rules if r.id == entry.rule_id), None)
                    if rule:
                        st.json({
                            "partner_id": entry.partner_id,
                            "rule_name": rule.name,
                            "model_type": rule.model_type.value,
                            "config": rule.config,
                            "split_percentage": entry.split_percentage,
                            "attributed_value": entry.attributed_value,
                            "audit_trail": entry.audit_trail
                        })

        else:
            st.warning("No attribution calculated for this deal. Run attribution calculation in the Ledger Explorer tab.")

        # Manual Override Section
        st.markdown("---")
        st.markdown("### 🛠️ Manual Attribution Override")

        with st.expander("⚠️ Adjust Attribution Manually (Advanced)"):
            st.warning("**Use with caution!** Manual overrides bypass attribution rules and are recorded in the audit trail.")

            st.markdown("**When to use manual overrides:**")
            st.markdown("""
            - Partner disputes that require special handling
            - One-time exceptional circumstances
            - Corrections to data entry errors
            - Executive decisions that override standard rules
            """)

            if deal_ledger:
                st.markdown("#### Current Attribution")

                # Create editable form
                with st.form(key=f"override_form_{selected_target_id}"):
                    st.markdown("Adjust the split percentages below. They must sum to 100%.")

                    override_splits = {}
                    total_percentage = 0

                    for entry in sorted(deal_ledger, key=lambda e: e.attributed_value, reverse=True):
                        partner_name = st.session_state.partners.get(entry.partner_id, entry.partner_id)
                        current_percent = entry.split_percentage * 100

                        override_col1, override_col2 = st.columns([3, 1])

                        with override_col1:
                            st.markdown(f"**{partner_name}** ({entry.partner_id})")

                        with override_col2:
                            new_percent = st.number_input(
                                f"Split % for {partner_name}",
                                min_value=0.0,
                                max_value=100.0,
                                value=current_percent,
                                step=0.1,
                                format="%.1f",
                                key=f"override_{entry.partner_id}_{selected_target_id}_{entry.id}",
                                label_visibility="collapsed"
                            )
                            override_splits[entry.partner_id] = new_percent / 100.0
                            total_percentage += new_percent

                    # Show total validation
                    if abs(total_percentage - 100.0) > 0.1:
                        st.error(f"⚠️ Total must equal 100%. Current total: {total_percentage:.1f}%")
                        submit_disabled = True
                    else:
                        st.success(f"✓ Total: {total_percentage:.1f}%")
                        submit_disabled = False

                    # Override reason
                    override_reason = st.text_area(
                        "Reason for Override (Required)",
                        placeholder="Explain why manual override is necessary...",
                        help="This will be recorded in the audit trail for compliance"
                    )

                    submit_col1, submit_col2 = st.columns([1, 1])

                    with submit_col1:
                        submit_override = st.form_submit_button(
                            "Apply Override",
                            type="primary" if not submit_disabled else None,
                            disabled=submit_disabled or not override_reason,
                            use_container_width=True
                        )

                    with submit_col2:
                        if st.form_submit_button("Reset to Calculated", use_container_width=True):
                            st.info("Recalculate attribution in the Ledger Explorer to restore automatic calculations.")

                if submit_override and override_reason:
                    # Apply manual overrides
                    current_user = "admin"  # TODO: Replace with actual user when auth is implemented

                    # Remove old ledger entries for this deal
                    st.session_state.ledger = [e for e in st.session_state.ledger if e.target_id != selected_target_id]

                    # Create new ledger entries with manual override
                    next_ledger_id = max([e.id for e in st.session_state.ledger], default=0) + 1

                    for partner_id, split_pct in override_splits.items():
                        if split_pct > 0:  # Only create entries for non-zero splits
                            # Find original entry to get rule_id
                            original_entry = next((e for e in deal_ledger if e.partner_id == partner_id), None)
                            rule_id = original_entry.rule_id if original_entry else 0

                            override_entry = LedgerEntry(
                                id=next_ledger_id,
                                target_id=selected_target_id,
                                partner_id=partner_id,
                                attributed_value=selected_target.value * split_pct,
                                split_percentage=split_pct,
                                rule_id=rule_id,
                                calculation_timestamp=datetime.now(),
                                override_by=current_user,
                                override_reason=override_reason,
                                audit_trail={
                                    "method": "manual_override",
                                    "override_by": current_user,
                                    "override_reason": override_reason,
                                    "override_timestamp": datetime.now().isoformat(),
                                    "original_split": next((e.split_percentage for e in deal_ledger if e.partner_id == partner_id), None)
                                }
                            )

                            st.session_state.ledger.append(override_entry)
                            next_ledger_id += 1

                    st.success(f"✅ Manual override applied! {len([s for s in override_splits.values() if s > 0])} partners updated.")
                    st.balloons()
                    st.rerun()

            else:
                st.info("No attribution calculated yet. Run attribution calculation first.")

        # Export Deal Report
        st.markdown("---")
        st.markdown("### Export Deal Report")

        if deal_ledger:
            export_col1, export_col2 = st.columns([3, 1])

            with export_col1:
                st.info("Generate a detailed PDF report for this deal, perfect for sharing with partners or resolving disputes.")

            with export_col2:
                # Generate simple CSV export for now
                deal_export_df = pd.DataFrame(attribution_data) if deal_ledger else pd.DataFrame()

                if not deal_export_df.empty:
                    csv_data = deal_export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download CSV",
                        data=csv_data,
                        file_name=f"deal_{selected_target.external_id}_attribution.csv",
                        mime="text/csv",
                        use_container_width=True
                    )


# ============================================================================
# TAB 8: LEDGER EXPLORER (was TAB 7, was TAB 5)
# ============================================================================

with tabs[8]:
    st.title("🔍 Attribution Ledger Explorer")
    st.caption("Immutable audit trail of all attribution calculations")

    if st.button("🔄 Recalculate Attribution", type="primary"):
        with st.spinner("Calculating..."):
            count = calculate_attribution_for_all_targets()
            st.success(f"✅ Created {count} new ledger entries")
            st.rerun()

    if st.session_state.ledger:
        st.markdown(f"### Ledger Entries ({len(st.session_state.ledger)})")

        ledger_df = pd.DataFrame([
            {
                "ID": entry.id,
                "Target ID": entry.target_id,
                "Partner": st.session_state.partners.get(entry.partner_id, entry.partner_id),
                "Attributed Value": f"${entry.attributed_value:,.2f}",
                "Split %": f"{entry.split_percentage:.1%}",
                "Rule ID": entry.rule_id,
                "Timestamp": entry.calculation_timestamp.strftime("%Y-%m-%d %H:%M")
            }
            for entry in st.session_state.ledger[-100:]  # Show last 100
        ])

        st.dataframe(ledger_df, use_container_width=True)

        # Export ledger
        if st.button("Download Full Ledger (CSV)"):
            full_df = pd.DataFrame([e.to_dict() for e in st.session_state.ledger])
            csv = full_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download",
                data=csv,
                file_name=f"ledger_{date.today()}.csv",
                mime="text/csv"
            )
    else:
        st.info("Ledger is empty. Import data and create rules, then click 'Recalculate Attribution'.")
