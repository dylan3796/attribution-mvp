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


# Main tabs - Simplified for better UX
# Startup-friendly: 5 tabs with progressive disclosure
# Enterprise features hidden in Settings expanders
tabs = st.tabs([
    "📊 Dashboard",      # Tab 0: Executive overview + key metrics
    "💼 Deals",          # Tab 1: Deal/opportunity management
    "🤝 Partners",       # Tab 2: Partner performance
    "📥 Data",           # Tab 3: Import data + rules
    "⚙️ Settings"        # Tab 4: Advanced config (progressive disclosure)
])


# ============================================================================
# TAB 0: DASHBOARD
# ============================================================================

with tabs[0]:
    st.header("Executive Dashboard")
    
    # Quick start for new users
    if len(st.session_state.targets) == 0:
        st.info("""
        **Welcome!** Get started by loading demo data or importing your own.
        
        1. Go to the **Data** tab
        2. Click **Load Demo Data** or upload a CSV
        3. Return here to see your attribution dashboard
        """)
        
        if st.button("Load Demo Data Now", type="primary"):
            with st.spinner("Loading demo data..."):
                demo_data = generate_complete_demo_data()
                st.session_state.session_manager.load_demo_data(demo_data)
                calculate_attribution_for_all_targets()
            st.success("Demo data loaded!")
            st.rerun()
    
    # Date range from global filters
    start_date, end_date = st.session_state.global_filters["date_range"]
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, datetime.min.time())
    if isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, datetime.max.time())
    
    # Get data
    revenue_df = get_revenue_as_dataframe()
    attribution_df = get_ledger_as_dataframe()
    
    if len(st.session_state.targets) > 0:
        # Apply filters
        filtered_ledger = apply_global_filters(st.session_state.ledger)
        
        # Build filtered attribution DataFrame
        if filtered_ledger:
            filtered_rows = []
            for entry in filtered_ledger:
                target = next((t for t in st.session_state.targets if t.id == entry.target_id), None)
                if target:
                    filtered_rows.append({
                        "partner_id": entry.partner_id,
                        "partner_name": st.session_state.partners.get(entry.partner_id, entry.partner_id),
                        "attributed_amount": entry.attributed_value,
                        "split_percent": entry.split_percentage,
                        "revenue_date": target.timestamp.date() if isinstance(target.timestamp, datetime) else target.timestamp,
                        "account_id": target.metadata.get("account_id", "unknown"),
                    })
            attribution_df = pd.DataFrame(filtered_rows)
        
        # Filter revenue by date
        if not revenue_df.empty:
            revenue_df = revenue_df[
                (pd.to_datetime(revenue_df["revenue_date"]) >= pd.to_datetime(start_date)) &
                (pd.to_datetime(revenue_df["revenue_date"]) <= pd.to_datetime(end_date))
            ]
        
        # Aggregate attribution by partner
        if not attribution_df.empty:
            attribution_agg = attribution_df.groupby(["partner_id", "partner_name"]).agg({
                "attributed_amount": "sum"
            }).reset_index()
        else:
            attribution_agg = pd.DataFrame(columns=["partner_id", "partner_name", "attributed_amount"])
        
        # Key Metrics
        st.subheader("Key Metrics")
        
        total_revenue = float(revenue_df["amount"].sum()) if not revenue_df.empty else 0.0
        total_attributed = float(attribution_agg["attributed_amount"].sum()) if not attribution_agg.empty else 0.0
        coverage = (total_attributed / total_revenue * 100) if total_revenue > 0 else 0.0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"${total_revenue:,.0f}")
        m2.metric("Attributed Revenue", f"${total_attributed:,.0f}", delta=f"{coverage:.0f}% coverage")
        m3.metric("Deals", len(st.session_state.targets))
        m4.metric("Active Partners", len(attribution_agg))
        
        st.markdown("---")
        
        # Charts
        st.subheader("Revenue & Attribution")
        
        chart1, chart2 = st.columns(2)
        
        with chart1:
            if not revenue_df.empty:
                st.plotly_chart(create_revenue_over_time_chart(revenue_df), use_container_width=True, key="dash_rev")
            else:
                st.info("No revenue data")
        
        with chart2:
            if not attribution_agg.empty:
                st.plotly_chart(create_attribution_pie_chart(attribution_agg), use_container_width=True, key="dash_attr")
            else:
                st.info("No attribution data")
        
        # Top Partners
        if not attribution_agg.empty:
            st.markdown("---")
            st.subheader("Top Partners")
            
            top_partners = attribution_agg.nlargest(10, "attributed_amount")
            top_partners["attributed_amount"] = top_partners["attributed_amount"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(
                top_partners[["partner_name", "attributed_amount"]].rename(columns={
                    "partner_name": "Partner",
                    "attributed_amount": "Attributed Revenue"
                }),
                use_container_width=True,
                hide_index=True
            )
        
        # Export
        with st.expander("Export Dashboard Data"):
            col1, col2 = st.columns(2)
            with col1:
                if not attribution_df.empty:
                    csv_data = export_to_csv(attribution_df, "attribution.csv")
                    st.download_button("Download Attribution CSV", csv_data, "attribution.csv", "text/csv")
            with col2:
                if not revenue_df.empty:
                    excel_data = export_to_excel({"Revenue": revenue_df, "Attribution": attribution_df})
                    st.download_button("Download Excel Report", excel_data, "report.xlsx")


# ============================================================================
# TAB 1: DEALS
# ============================================================================

with tabs[1]:
    st.header("Deals")
    st.caption("View and manage attribution targets (opportunities/deals)")
    
    if not st.session_state.targets:
        st.info("No deals loaded. Go to the **Data** tab to import data.")
    else:
        # Search
        search = st.text_input("Search deals", placeholder="Search by ID, account, or partner...")
        
        # Build deals table
        deals_data = []
        for target in st.session_state.targets:
            touchpoints = [tp for tp in st.session_state.touchpoints if tp.target_id == target.id]
            partner_names = [st.session_state.partners.get(tp.partner_id, tp.partner_id) for tp in touchpoints]
            ledger_entries = [e for e in st.session_state.ledger if e.target_id == target.id]
            attributed = sum(e.attributed_value for e in ledger_entries)
            
            deals_data.append({
                "ID": target.id,
                "External ID": target.external_id or "-",
                "Account": target.metadata.get("account_id", "-"),
                "Value": f"${target.value:,.0f}",
                "Date": target.timestamp.strftime("%Y-%m-%d") if isinstance(target.timestamp, datetime) else str(target.timestamp),
                "Partners": ", ".join(partner_names[:3]) + ("..." if len(partner_names) > 3 else "") if partner_names else "None",
                "Attributed": f"${attributed:,.0f}"
            })
        
        deals_df = pd.DataFrame(deals_data)
        
        # Apply search
        if search:
            mask = deals_df.apply(lambda row: search.lower() in str(row).lower(), axis=1)
            deals_df = deals_df[mask]
        
        st.dataframe(deals_df, use_container_width=True, hide_index=True)
        
        # Deal details expander
        with st.expander("Deal Details"):
            if deals_data:
                selected_id = st.selectbox("Select Deal", [d["ID"] for d in deals_data], key="deal_select")
                target = next((t for t in st.session_state.targets if t.id == selected_id), None)
                
                if target:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Deal Info**")
                        st.write(f"Value: ${target.value:,.0f}")
                        st.write(f"Date: {target.timestamp}")
                        st.write(f"Account: {target.metadata.get('account_id', 'N/A')}")
                        st.write(f"External ID: {target.external_id or 'N/A'}")
                    
                    with col2:
                        st.markdown("**Partners Involved**")
                        touchpoints = [tp for tp in st.session_state.touchpoints if tp.target_id == selected_id]
                        if touchpoints:
                            for tp in touchpoints:
                                partner_name = st.session_state.partners.get(tp.partner_id, tp.partner_id)
                                st.write(f"• {partner_name} ({tp.role})")
                        else:
                            st.info("No partners linked")


# ============================================================================
# TAB 2: PARTNERS
# ============================================================================

with tabs[2]:
    st.header("Partners")
    st.caption("Manage partners and view performance")
    
    # Add partner
    with st.expander("Add New Partner", expanded=len(st.session_state.partners) < 5):
        with st.form("add_partner_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_partner_id = st.text_input("Partner ID", placeholder="P-001")
            with col2:
                new_partner_name = st.text_input("Partner Name", placeholder="Acme Consulting")
            
            if st.form_submit_button("Add Partner", type="primary"):
                if new_partner_id and new_partner_name:
                    st.session_state.session_manager.add_partner(new_partner_id, new_partner_name)
                    st.success(f"Added partner: {new_partner_name}")
                    st.rerun()
                else:
                    st.error("Both ID and name are required")
    
    st.markdown("---")
    
    # Partner performance table
    st.subheader("Partner Performance")
    
    attribution_df = get_ledger_as_dataframe()
    partner_data = []
    
    for pid, pname in st.session_state.partners.items():
        partner_ledger = attribution_df[attribution_df["partner_id"] == pid] if not attribution_df.empty else pd.DataFrame()
        attributed = float(partner_ledger["attributed_amount"].sum()) if not partner_ledger.empty else 0.0
        deals_count = len([tp for tp in st.session_state.touchpoints if tp.partner_id == pid])
        
        partner_data.append({
            "ID": pid,
            "Partner": pname,
            "Deals": deals_count,
            "Attributed Revenue": f"${attributed:,.0f}"
        })
    
    if partner_data:
        partner_df = pd.DataFrame(partner_data)
        st.dataframe(partner_df, use_container_width=True, hide_index=True)
        
        # Partner detail view
        with st.expander("Partner Details"):
            selected_partner = st.selectbox("Select Partner", [p["Partner"] for p in partner_data], key="partner_select")
            partner_id = next((p["ID"] for p in partner_data if p["Partner"] == selected_partner), None)
            
            if partner_id:
                st.markdown(f"**Deals linked to {selected_partner}:**")
                partner_touchpoints = [tp for tp in st.session_state.touchpoints if tp.partner_id == partner_id]
                
                if partner_touchpoints:
                    for tp in partner_touchpoints[:15]:
                        target = next((t for t in st.session_state.targets if t.id == tp.target_id), None)
                        if target:
                            st.write(f"• {target.external_id or target.id}: ${target.value:,.0f} ({tp.role})")
                else:
                    st.info("No deals linked")
    else:
        st.info("No partners yet. Add one above!")


# ============================================================================
# TAB 3: DATA
# ============================================================================

with tabs[3]:
    st.header("Data Management")
    st.caption("Import data and configure attribution rules")
    
    data_tabs = st.tabs(["📥 Import", "📋 Rules", "📄 Templates"])
    
    # Import subtab
    with data_tabs[0]:
        st.subheader("Quick Start")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Load Demo Data**")
            st.markdown("Get started instantly with sample data")
            if st.button("Load Demo Data", type="primary", use_container_width=True, key="load_demo"):
                with st.spinner("Loading..."):
                    demo_data = generate_complete_demo_data()
                    st.session_state.session_manager.load_demo_data(demo_data)
                    calculate_attribution_for_all_targets()
                st.success("Demo data loaded!")
                st.rerun()
        
        with col2:
            st.markdown("**Reset All Data**")
            st.markdown("Clear everything and start fresh")
            if st.button("Reset Data", type="secondary", use_container_width=True, key="reset_data"):
                st.session_state.session_manager.clear_all_data()
                st.success("Data cleared!")
                st.rerun()
        
        st.markdown("---")
        st.subheader("Upload CSV")
        
        upload_type = st.selectbox("Data Type", ["Targets (Deals/Opportunities)", "Touchpoints (Partner Links)"])
        uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.write("Preview:")
                st.dataframe(df.head())
                
                if st.button("Import Data", key="import_csv"):
                    with st.spinner("Importing..."):
                        csv_content = uploaded_file.getvalue().decode('utf-8')
                        data_type = "targets" if "Targets" in upload_type else "touchpoints"
                        result = ingest_csv(csv_content, data_type, st.session_state.session_manager)
                        
                        if result.get("success"):
                            calculate_attribution_for_all_targets()
                            st.success(f"Imported {result.get('count', 0)} records!")
                            st.rerun()
                        else:
                            st.error(f"Import failed: {result.get('error')}")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    # Rules subtab
    with data_tabs[1]:
        st.subheader("Attribution Rules")
        st.caption("Rules determine how revenue is split among partners")
        
        if st.session_state.rules:
            st.markdown("**Active Rules:**")
            for rule in st.session_state.rules:
                with st.expander(f"{rule.name} ({'Active' if rule.active else 'Inactive'})"):
                    st.write(f"Model: {rule.model.value}")
                    st.write(f"Priority: {rule.priority}")
                    if rule.config:
                        st.json(rule.config)
        else:
            st.info("No rules configured. Add one from templates below.")
        
        st.markdown("---")
        st.subheader("Add Rule from Template")
        
        available_templates = list_templates()
        if available_templates:
            template_options = {t['name']: t for t in available_templates}
            selected_template_name = st.selectbox(
                "Select Template",
                list(template_options.keys()),
                key="template_select"
            )
            
            if st.button("Apply Template", key="apply_template"):
                template = template_options[selected_template_name]
                rule = AttributionRule(
                    id=f"rule-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    name=template['name'],
                    model=AttributionModel(template.get('model', 'EQUAL_SPLIT')),
                    priority=len(st.session_state.rules) + 1,
                    config=template.get('config', {}),
                    active=True
                )
                st.session_state.session_manager.add_rule(rule)
                st.success(f"Added rule: {template['name']}")
                st.rerun()
        else:
            st.info("No templates available")
    
    # Templates subtab
    with data_tabs[2]:
        st.subheader("CSV Templates")
        st.caption("Download templates to format your data correctly")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Targets Template**")
            st.markdown("For deals/opportunities data")
            targets_csv = generate_csv_template("targets")
            st.download_button(
                "Download Targets Template",
                targets_csv,
                "targets_template.csv",
                "text/csv",
                use_container_width=True,
                key="dl_targets"
            )
        
        with col2:
            st.markdown("**Touchpoints Template**")
            st.markdown("For partner involvement data")
            touchpoints_csv = generate_csv_template("touchpoints")
            st.download_button(
                "Download Touchpoints Template",
                touchpoints_csv,
                "touchpoints_template.csv",
                "text/csv",
                use_container_width=True,
                key="dl_touchpoints"
            )


# ============================================================================
# TAB 4: SETTINGS (Progressive Disclosure)
# ============================================================================

with tabs[4]:
    st.header("Settings")
    st.caption("Configure your attribution system")
    
    # Basic settings (always visible)
    st.subheader("System Info")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Schema Version:** {SCHEMA_VERSION}")
        st.write(f"**Targets:** {len(st.session_state.targets)}")
        st.write(f"**Touchpoints:** {len(st.session_state.touchpoints)}")
    with col2:
        st.write(f"**Rules:** {len(st.session_state.rules)}")
        st.write(f"**Ledger Entries:** {len(st.session_state.ledger)}")
        st.write(f"**Partners:** {len(st.session_state.partners)}")
    
    st.markdown("---")
    
    # Recalculate attribution
    st.subheader("Attribution Actions")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Recalculate Attribution", use_container_width=True, key="recalc"):
            with st.spinner("Calculating..."):
                count = calculate_attribution_for_all_targets()
            st.success(f"Created {count} ledger entries")
            st.rerun()
    
    with col2:
        if st.button("Clear Ledger", use_container_width=True, key="clear_ledger"):
            st.session_state.ledger = []
            st.success("Ledger cleared")
            st.rerun()
    
    with col3:
        if st.button("Factory Reset", type="secondary", use_container_width=True, key="factory_reset"):
            st.session_state.session_manager.clear_all_data()
            st.success("All data reset")
            st.rerun()
    
    st.markdown("---")
    
    # Advanced features (collapsed by default)
    with st.expander("Approval Queue", expanded=False):
        st.markdown("#### Touchpoint Approvals")
        st.caption("Review and approve partner touchpoints requiring approval")
        
        pending = [tp for tp in st.session_state.touchpoints if getattr(tp, 'requires_approval', False)]
        if pending:
            for tp in pending[:10]:
                partner_name = st.session_state.partners.get(tp.partner_id, tp.partner_id)
                st.write(f"• {partner_name} on {tp.target_id} ({tp.role})")
        else:
            st.info("No pending approvals")
    
    with st.expander("Salesforce Integration", expanded=False):
        st.markdown("#### Connect to Salesforce")
        st.caption("Sync opportunities and partner data from your CRM")
        
        st.info("""
        **Salesforce Integration supports 3 segments:**
        
        1. **Segment 1:** Partner field already populated on opportunities
        2. **Segment 2:** Indirect attribution via activities, campaigns, contact roles
        3. **Segment 3:** Deal registrations (partner-submitted opportunities)
        
        Contact your administrator to configure OAuth credentials.
        """)
    
    with st.expander("Period Management", expanded=False):
        st.markdown("#### Attribution Periods")
        st.caption("Lock periods to prevent changes to historical attribution")
        
        st.info("Period management allows you to close and lock attribution periods for compliance and audit purposes.")
    
    with st.expander("Ledger Explorer", expanded=False):
        st.markdown("#### Attribution Ledger")
        st.caption("View all calculated attribution entries")
        
        if st.session_state.ledger:
            ledger_data = []
            for entry in st.session_state.ledger[-100:]:
                ledger_data.append({
                    "Target": entry.target_id,
                    "Partner": st.session_state.partners.get(entry.partner_id, entry.partner_id),
                    "Amount": f"${entry.attributed_value:,.0f}",
                    "Split": f"{entry.split_percentage:.1%}",
                    "Calculated": entry.calculation_timestamp.strftime("%Y-%m-%d %H:%M")
                })
            
            st.dataframe(pd.DataFrame(ledger_data), use_container_width=True, hide_index=True)
            
            # Export
            full_df = pd.DataFrame([{
                "target_id": e.target_id,
                "partner_id": e.partner_id,
                "partner_name": st.session_state.partners.get(e.partner_id, e.partner_id),
                "attributed_value": e.attributed_value,
                "split_percentage": e.split_percentage,
                "rule_id": e.rule_id,
                "timestamp": e.calculation_timestamp.isoformat()
            } for e in st.session_state.ledger])
            
            csv = full_df.to_csv(index=False)
            st.download_button("Export Full Ledger CSV", csv, "ledger.csv", "text/csv", key="export_ledger")
        else:
            st.info("No ledger entries. Import data and run attribution.")
    
    with st.expander("Audit Trail", expanded=False):
        st.markdown("#### Change History")
        st.caption("Track changes to attribution data")
        
        st.info("Audit trail shows all changes made to partners, rules, and attribution calculations.")
