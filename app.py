"""
Attribution MVP - Simplified Universal Architecture

A clean, intuitive interface for partner attribution.
Simple for startups. Powerful enough for enterprise.

Tab Structure:
1. Dashboard - Executive overview with key metrics
2. Deals - View and manage attribution targets
3. Partners - Partner performance and management
4. Data - Import data, configure rules
5. Settings - Advanced configuration (progressive disclosure)
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, date, timedelta
from typing import List
import warnings

warnings.filterwarnings('ignore')

# Universal architecture imports
from models_new import (
    AttributionTarget, PartnerTouchpoint, AttributionRule, LedgerEntry,
    TargetType, TouchpointType, AttributionModel, DEFAULT_PARTNER_ROLES
)
from attribution_engine import AttributionEngine
from data_ingestion import ingest_csv, generate_csv_template
from templates import list_templates, get_template
from demo_data import generate_complete_demo_data, get_demo_data_summary

# Dashboard visualizations
from dashboards import (
    create_revenue_over_time_chart,
    create_partner_performance_bar_chart,
    create_attribution_pie_chart,
    create_partner_role_distribution
)
from exports import export_to_csv, export_to_excel

# Database & session
from db_universal import Database
from session_manager import SessionManager

# Authentication
from login_page import (
    check_authentication, render_login_page,
    render_user_info_sidebar, can_user_approve_touchpoints
)

# Optional features (imported only when needed)
from approval_workflow import render_approval_queue, render_approval_history
from period_management import render_period_management

# ============================================================================
# Configuration
# ============================================================================

DB_PATH = "attribution.db"

# Authentication check
if not check_authentication(DB_PATH):
    render_login_page(DB_PATH)
    st.stop()

# Page setup
st.set_page_config(
    page_title="Partner Attribution",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Clean styling
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #fafbfc 0%, #f0f4f8 100%); }
    .stTabs [role="tablist"] { gap: 8px; border-bottom: 2px solid #e5e7eb; }
    .stTabs [role="tab"] { padding: 0.75rem 1.25rem; border-radius: 8px 8px 0 0; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: #3b82f6; color: white !important; }
    .quick-start { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Database & Session Initialization
# ============================================================================

if "db_initialized" not in st.session_state:
    db = Database(DB_PATH)
    db.init_db()
    st.session_state.db_initialized = True
    from auth import create_default_organization_and_admin
    create_default_organization_and_admin(DB_PATH)

if "session_manager" not in st.session_state:
    st.session_state.session_manager = SessionManager(DB_PATH)
    st.session_state.session_manager.initialize_session_state()

# Ensure demo partners exist
if not st.session_state.partners:
    demo_partners = {
        "P001": "CloudConsult Partners",
        "P002": "DataWorks SI",
        "P003": "AnalyticsPro",
        "P004": "TechAlliance Inc"
    }
    for pid, pname in demo_partners.items():
        st.session_state.session_manager.add_partner(pid, pname)

# ============================================================================
# Helper Functions
# ============================================================================

def calculate_attribution():
    """Run attribution calculations for all targets."""
    engine = AttributionEngine()
    return st.session_state.session_manager.recalculate_attribution(engine)

def get_ledger_df() -> pd.DataFrame:
    """Convert ledger to DataFrame."""
    if not st.session_state.ledger:
        return pd.DataFrame(columns=["partner_id", "partner_name", "attributed_amount", "revenue_date"])

    rows = []
    for entry in st.session_state.ledger:
        target = next((t for t in st.session_state.targets if t.id == entry.target_id), None)
        if not target:
            continue
        rows.append({
            "partner_id": entry.partner_id,
            "partner_name": st.session_state.partners.get(entry.partner_id, entry.partner_id),
            "attributed_amount": entry.attributed_value,
            "split_percent": entry.split_percentage,
            "revenue_date": target.timestamp.date() if isinstance(target.timestamp, datetime) else target.timestamp,
            "account_id": target.metadata.get("account_id", "unknown")
        })
    return pd.DataFrame(rows)

def get_revenue_df() -> pd.DataFrame:
    """Convert targets to revenue DataFrame."""
    if not st.session_state.targets:
        return pd.DataFrame(columns=["revenue_date", "amount", "account_id"])

    return pd.DataFrame([{
        "revenue_date": t.timestamp.date() if isinstance(t.timestamp, datetime) else t.timestamp,
        "amount": t.value,
        "account_id": t.metadata.get("account_id", "unknown")
    } for t in st.session_state.targets])

# Check if fresh install
is_fresh = len(st.session_state.targets) == 0

# ============================================================================
# Main App
# ============================================================================

st.title("Partner Attribution")

# Sidebar - simplified
with st.sidebar:
    render_user_info_sidebar()

    st.markdown("### Quick Stats")
    st.metric("Deals", len(st.session_state.targets))
    st.metric("Partners", len(st.session_state.partners))
    st.metric("Ledger Entries", len(st.session_state.ledger))

    if st.button("Recalculate Attribution", use_container_width=True):
        entries = calculate_attribution()
        st.success(f"Created {entries} entries")
        st.rerun()

# ============================================================================
# Tab Structure - Simplified to 5 tabs
# ============================================================================

tabs = st.tabs([
    "📊 Dashboard",
    "💼 Deals",
    "🤝 Partners",
    "📥 Data",
    "⚙️ Settings"
])

# ============================================================================
# TAB 1: DASHBOARD
# ============================================================================

with tabs[0]:
    # Quick Start for new users
    if is_fresh:
        st.markdown("""
        <div class="quick-start">
            <h3 style="margin:0 0 0.5rem 0; color:white;">Welcome! Let's get you started</h3>
            <p style="margin:0; opacity:0.9;">Load demo data or import your own to see attribution in action.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Step 1: Load Data**")
            st.markdown("Go to the Data tab to import deals and partners")
        with col2:
            st.markdown("**Step 2: Configure Rules**")
            st.markdown("Set up attribution rules in the Data tab")
        with col3:
            st.markdown("**Step 3: View Results**")
            st.markdown("Return here to see your attribution dashboard")

        if st.button("Load Demo Data Now", type="primary"):
            with st.spinner("Loading demo data..."):
                demo_data = generate_complete_demo_data()
                st.session_state.session_manager.load_demo_data(demo_data)
                calculate_attribution()
            st.success("Demo data loaded!")
            st.rerun()

        st.markdown("---")

    # Time period selector
    col1, col2 = st.columns([2, 6])
    with col1:
        days = st.selectbox("Period", [7, 30, 60, 90], index=1, format_func=lambda x: f"Last {x} days")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get data
    revenue_df = get_revenue_df()
    ledger_df = get_ledger_df()

    # Filter by date
    if not revenue_df.empty:
        revenue_df = revenue_df[
            (pd.to_datetime(revenue_df["revenue_date"]) >= pd.to_datetime(start_date)) &
            (pd.to_datetime(revenue_df["revenue_date"]) <= pd.to_datetime(end_date))
        ]

    if not ledger_df.empty:
        ledger_df = ledger_df[
            (pd.to_datetime(ledger_df["revenue_date"]) >= pd.to_datetime(start_date)) &
            (pd.to_datetime(ledger_df["revenue_date"]) <= pd.to_datetime(end_date))
        ]

    # Key Metrics
    st.markdown("### Key Metrics")

    total_revenue = float(revenue_df["amount"].sum()) if not revenue_df.empty else 0.0
    total_attributed = float(ledger_df["attributed_amount"].sum()) if not ledger_df.empty else 0.0
    coverage = (total_attributed / total_revenue * 100) if total_revenue > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"${total_revenue:,.0f}")
    m2.metric("Attributed", f"${total_attributed:,.0f}", delta=f"{coverage:.0f}% coverage")
    m3.metric("Deals", len(st.session_state.targets))
    m4.metric("Active Partners", ledger_df["partner_id"].nunique() if not ledger_df.empty else 0)

    # Charts
    if not revenue_df.empty or not ledger_df.empty:
        st.markdown("---")

        chart1, chart2 = st.columns(2)

        with chart1:
            st.markdown("#### Revenue Trend")
            if not revenue_df.empty:
                st.plotly_chart(create_revenue_over_time_chart(revenue_df), use_container_width=True)
            else:
                st.info("No revenue data")

        with chart2:
            st.markdown("#### Attribution by Partner")
            if not ledger_df.empty:
                agg_df = ledger_df.groupby(["partner_id", "partner_name"]).agg({
                    "attributed_amount": "sum"
                }).reset_index()
                st.plotly_chart(create_attribution_pie_chart(agg_df), use_container_width=True)
            else:
                st.info("No attribution data")

        # Top Partners
        if not ledger_df.empty:
            st.markdown("---")
            st.markdown("#### Top Partners")

            top_partners = ledger_df.groupby("partner_name")["attributed_amount"].sum().sort_values(ascending=False).head(5)
            top_df = pd.DataFrame({
                "Partner": top_partners.index,
                "Attributed Revenue": top_partners.values
            })
            top_df["Attributed Revenue"] = top_df["Attributed Revenue"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(top_df, use_container_width=True, hide_index=True)

    # Export
    with st.expander("Export Data"):
        col1, col2 = st.columns(2)
        with col1:
            if not ledger_df.empty:
                csv = export_to_csv(ledger_df, "attribution.csv")
                st.download_button("Download CSV", csv, "attribution.csv", "text/csv")
        with col2:
            if not ledger_df.empty:
                excel = export_to_excel({"Attribution": ledger_df, "Revenue": revenue_df})
                st.download_button("Download Excel", excel, "report.xlsx")

# ============================================================================
# TAB 2: DEALS
# ============================================================================

with tabs[1]:
    st.markdown("### Deals (Attribution Targets)")
    st.caption("View all deals/opportunities and their attribution status")

    if not st.session_state.targets:
        st.info("No deals loaded. Go to the Data tab to import data or load demo data.")
    else:
        # Filter
        col1, col2 = st.columns([2, 4])
        with col1:
            search = st.text_input("Search deals", placeholder="Search by ID or name...")

        # Build deals table
        deals_data = []
        for target in st.session_state.targets:
            # Find touchpoints for this target
            touchpoints = [tp for tp in st.session_state.touchpoints if tp.target_id == target.id]
            partner_names = [st.session_state.partners.get(tp.partner_id, tp.partner_id) for tp in touchpoints]

            # Find ledger entries
            ledger_entries = [e for e in st.session_state.ledger if e.target_id == target.id]
            attributed = sum(e.attributed_value for e in ledger_entries)

            deals_data.append({
                "ID": target.id,
                "External ID": target.external_id or "-",
                "Value": f"${target.value:,.0f}",
                "Date": target.timestamp.strftime("%Y-%m-%d") if isinstance(target.timestamp, datetime) else str(target.timestamp),
                "Partners": ", ".join(partner_names[:3]) + ("..." if len(partner_names) > 3 else "") if partner_names else "None",
                "Attributed": f"${attributed:,.0f}"
            })

        deals_df = pd.DataFrame(deals_data)

        # Apply search filter
        if search:
            mask = deals_df.apply(lambda row: search.lower() in str(row).lower(), axis=1)
            deals_df = deals_df[mask]

        st.dataframe(deals_df, use_container_width=True, hide_index=True)

        # Deal details
        with st.expander("Deal Details"):
            if deals_data:
                selected_id = st.selectbox("Select Deal", [d["ID"] for d in deals_data])

                target = next((t for t in st.session_state.targets if t.id == selected_id), None)
                if target:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Deal Info**")
                        st.write(f"Value: ${target.value:,.0f}")
                        st.write(f"Date: {target.timestamp}")
                        st.write(f"Account: {target.metadata.get('account_id', 'N/A')}")

                    with col2:
                        st.markdown("**Partners**")
                        touchpoints = [tp for tp in st.session_state.touchpoints if tp.target_id == selected_id]
                        if touchpoints:
                            for tp in touchpoints:
                                st.write(f"• {st.session_state.partners.get(tp.partner_id, tp.partner_id)} ({tp.role})")
                        else:
                            st.info("No partners linked")

# ============================================================================
# TAB 3: PARTNERS
# ============================================================================

with tabs[2]:
    st.markdown("### Partners")
    st.caption("Manage partners and view performance")

    # Add partner
    with st.expander("Add New Partner", expanded=len(st.session_state.partners) < 5):
        with st.form("add_partner", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                partner_id = st.text_input("Partner ID", placeholder="P-001")
            with col2:
                partner_name = st.text_input("Partner Name", placeholder="Acme Consulting")

            if st.form_submit_button("Add Partner", type="primary"):
                if partner_id and partner_name:
                    st.session_state.session_manager.add_partner(partner_id, partner_name)
                    st.success(f"Added {partner_name}")
                    st.rerun()
                else:
                    st.error("Both ID and name required")

    st.markdown("---")

    # Partner list with performance
    st.markdown("#### Partner Performance")

    partner_data = []
    ledger_df = get_ledger_df()

    for pid, pname in st.session_state.partners.items():
        # Calculate metrics
        partner_ledger = ledger_df[ledger_df["partner_id"] == pid] if not ledger_df.empty else pd.DataFrame()
        attributed = partner_ledger["attributed_amount"].sum() if not partner_ledger.empty else 0
        deals = len([tp for tp in st.session_state.touchpoints if tp.partner_id == pid])

        partner_data.append({
            "ID": pid,
            "Name": pname,
            "Deals": deals,
            "Attributed Revenue": f"${attributed:,.0f}"
        })

    if partner_data:
        partner_df = pd.DataFrame(partner_data)
        st.dataframe(partner_df, use_container_width=True, hide_index=True)

        # Partner details
        with st.expander("Partner Details"):
            selected_partner = st.selectbox("Select Partner", [p["Name"] for p in partner_data])
            partner_id = next((p["ID"] for p in partner_data if p["Name"] == selected_partner), None)

            if partner_id:
                # Show deals for this partner
                partner_touchpoints = [tp for tp in st.session_state.touchpoints if tp.partner_id == partner_id]

                st.markdown(f"**Deals linked to {selected_partner}:**")
                if partner_touchpoints:
                    for tp in partner_touchpoints[:10]:
                        target = next((t for t in st.session_state.targets if t.id == tp.target_id), None)
                        if target:
                            st.write(f"• {target.external_id or target.id}: ${target.value:,.0f} ({tp.role})")
                else:
                    st.info("No deals linked to this partner")
    else:
        st.info("No partners yet. Add one above!")

# ============================================================================
# TAB 4: DATA
# ============================================================================

with tabs[3]:
    st.markdown("### Data Management")
    st.caption("Import data and configure attribution rules")

    data_tabs = st.tabs(["📥 Import", "📋 Rules", "📄 Templates"])

    # Import tab
    with data_tabs[0]:
        st.markdown("#### Quick Start")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Load Demo Data**")
            st.markdown("Get started instantly with sample data")
            if st.button("Load Demo Data", type="primary", use_container_width=True):
                with st.spinner("Loading..."):
                    demo_data = generate_complete_demo_data()
                    st.session_state.session_manager.load_demo_data(demo_data)
                    calculate_attribution()
                st.success("Demo data loaded!")
                st.rerun()

        with col2:
            st.markdown("**Reset All Data**")
            st.markdown("Clear everything and start fresh")
            if st.button("Reset Data", type="secondary", use_container_width=True):
                st.session_state.session_manager.clear_all_data()
                st.success("Data cleared!")
                st.rerun()

        st.markdown("---")
        st.markdown("#### Upload CSV")

        upload_type = st.selectbox("Data Type", ["Targets (Deals)", "Touchpoints (Partner Links)"])

        uploaded = st.file_uploader("Upload CSV file", type=['csv'])

        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.write("Preview:")
                st.dataframe(df.head())

                if st.button("Import Data"):
                    with st.spinner("Importing..."):
                        if "Targets" in upload_type:
                            result = ingest_csv(df.to_csv(index=False), "targets")
                        else:
                            result = ingest_csv(df.to_csv(index=False), "touchpoints")

                        if result.get("success"):
                            st.success(f"Imported {result.get('count', 0)} records")
                            calculate_attribution()
                            st.rerun()
                        else:
                            st.error(f"Import failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error reading file: {e}")

    # Rules tab
    with data_tabs[1]:
        st.markdown("#### Attribution Rules")
        st.caption("Rules determine how revenue is split among partners")

        # Current rules
        if st.session_state.rules:
            st.markdown("**Active Rules:**")
            for rule in st.session_state.rules:
                with st.expander(f"{rule.name} ({'Active' if rule.active else 'Inactive'})"):
                    st.write(f"Model: {rule.model.value}")
                    st.write(f"Priority: {rule.priority}")
                    if rule.config:
                        st.json(rule.config)
        else:
            st.info("No rules configured. Add a template below.")

        st.markdown("---")
        st.markdown("#### Add Rule from Template")

        templates = list_templates()
        if templates:
            selected_template = st.selectbox(
                "Select Template",
                templates,
                format_func=lambda t: f"{t['name']} - {t.get('description', '')}"
            )

            if st.button("Apply Template"):
                template = get_template(selected_template['id'])
                if template:
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

    # Templates tab
    with data_tabs[2]:
        st.markdown("#### CSV Templates")
        st.caption("Download templates for data import")

        col1, col2 = st.columns(2)

        with col1:
            targets_template = generate_csv_template("targets")
            st.download_button(
                "Download Targets Template",
                targets_template,
                "targets_template.csv",
                "text/csv",
                use_container_width=True
            )

        with col2:
            touchpoints_template = generate_csv_template("touchpoints")
            st.download_button(
                "Download Touchpoints Template",
                touchpoints_template,
                "touchpoints_template.csv",
                "text/csv",
                use_container_width=True
            )

# ============================================================================
# TAB 5: SETTINGS
# ============================================================================

with tabs[4]:
    st.markdown("### Settings")
    st.caption("Configure your attribution system")

    # Basic settings (always visible)
    st.markdown("#### Basic Settings")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Default Partner Roles**")
        for role in DEFAULT_PARTNER_ROLES:
            st.write(f"• {role}")

    with col2:
        st.markdown("**System Info**")
        st.write(f"Targets loaded: {len(st.session_state.targets)}")
        st.write(f"Touchpoints: {len(st.session_state.touchpoints)}")
        st.write(f"Rules: {len(st.session_state.rules)}")
        st.write(f"Ledger entries: {len(st.session_state.ledger)}")

    st.markdown("---")

    # Advanced settings (collapsed)
    with st.expander("Advanced: Approval Queue", expanded=False):
        st.markdown("#### Touchpoint Approvals")
        st.caption("Review and approve partner touchpoints")

        if can_user_approve_touchpoints():
            pending = [tp for tp in st.session_state.touchpoints if getattr(tp, 'requires_approval', False)]
            if pending:
                render_approval_queue(pending)
            else:
                st.info("No pending approvals")
        else:
            st.warning("You don't have approval permissions")

    with st.expander("Advanced: Period Management", expanded=False):
        st.markdown("#### Attribution Periods")
        st.caption("Lock periods to prevent changes to historical data")
        render_period_management()

    with st.expander("Advanced: Ledger Explorer", expanded=False):
        st.markdown("#### Attribution Ledger")
        st.caption("View all calculated attribution entries")

        if st.session_state.ledger:
            ledger_data = []
            for entry in st.session_state.ledger[:100]:  # Limit to 100
                ledger_data.append({
                    "Target": entry.target_id,
                    "Partner": st.session_state.partners.get(entry.partner_id, entry.partner_id),
                    "Amount": f"${entry.attributed_value:,.0f}",
                    "Split": f"{entry.split_percentage:.1%}",
                    "Calculated": entry.calculation_timestamp.strftime("%Y-%m-%d %H:%M")
                })

            st.dataframe(pd.DataFrame(ledger_data), use_container_width=True, hide_index=True)

            # Export
            csv = export_to_csv(get_ledger_df(), "ledger.csv")
            st.download_button("Export Ledger CSV", csv, "ledger.csv", "text/csv")
        else:
            st.info("No ledger entries yet. Import data and run attribution.")

    with st.expander("Advanced: Audit Trail", expanded=False):
        st.markdown("#### Change History")
        st.caption("Track all changes to attribution data")

        # Show recent changes from session history if available
        if hasattr(st.session_state, 'audit_log') and st.session_state.audit_log:
            st.dataframe(pd.DataFrame(st.session_state.audit_log[-50:]), use_container_width=True)
        else:
            st.info("Audit trail will show changes as you use the system")

    st.markdown("---")

    # System actions
    st.markdown("#### System Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Recalculate All", use_container_width=True):
            entries = calculate_attribution()
            st.success(f"Created {entries} ledger entries")

    with col2:
        if st.button("Clear Ledger Only", use_container_width=True):
            st.session_state.ledger = []
            st.success("Ledger cleared")

    with col3:
        if st.button("Factory Reset", use_container_width=True, type="secondary"):
            st.session_state.session_manager.clear_all_data()
            st.success("All data reset")
            st.rerun()
