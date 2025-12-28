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

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Attribution MVP - Universal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Preserve original styling
st.markdown("""
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


# ============================================================================
# Main App
# ============================================================================

st.title("🎯 Attribution MVP - Universal Architecture")
st.caption("Config-driven partner attribution with CSV upload, templates, and natural language rules")

# Sidebar stats
with st.sidebar:
    st.markdown("### Quick Stats")
    st.metric("Targets Loaded", len(st.session_state.targets))
    st.metric("Touchpoints", len(st.session_state.touchpoints))
    st.metric("Active Rules", len([r for r in st.session_state.rules if r.active]))
    st.metric("Ledger Entries", len(st.session_state.ledger))

    st.markdown("---")
    st.markdown("### Architecture")
    st.info(f"""
**Schema Version:** {SCHEMA_VERSION}

**Tables:**
- AttributionTarget
- PartnerTouchpoint
- AttributionRule
- AttributionLedger
    """)


# Main tabs
tabs = st.tabs([
    "📊 Dashboard",
    "📥 Data Import",
    "⚙️ Rule Builder",
    "📋 Rules & Templates",
    "💰 Deal Drilldown",
    "🔍 Ledger Explorer"
])


# ============================================================================
# TAB 0: DASHBOARD (PRESERVED FROM ORIGINAL)
# ============================================================================

with tabs[0]:
    st.title("Attribution Dashboard")
    st.caption("Executive overview of partner attribution performance and metrics")

    # Enhanced Date Range Selector
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        period_type = st.selectbox(
            "Period Type",
            ["Quick Range", "Month", "Quarter", "Year", "Custom"],
            help="Select how you want to define the reporting period"
        )

    with col2:
        if period_type == "Quick Range":
            days = st.selectbox(
                "Time Range",
                [7, 30, 60, 90, 180],
                index=1,
                format_func=lambda x: f"Last {x} days"
            )
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

        elif period_type == "Month":
            # Generate last 12 months
            months = []
            today = date.today()
            for i in range(12):
                month_date = today.replace(day=1) - timedelta(days=i*30)
                months.append((month_date.strftime("%B %Y"), month_date.year, month_date.month))

            selected_month = st.selectbox(
                "Select Month",
                [m[0] for m in months],
                help="Choose a specific month for reporting"
            )

            # Find selected month details
            year, month = next((m[1], m[2]) for m in months if m[0] == selected_month)
            start_date = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)

        elif period_type == "Quarter":
            # Generate last 4 quarters
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
                help="Choose a specific quarter for reporting"
            )

            # Calculate quarter dates
            year, quarter = next((q[1], q[2]) for q in quarters if q[0] == selected_quarter)
            start_month = (quarter - 1) * 3 + 1
            start_date = date(year, start_month, 1)
            end_month = start_month + 2
            last_day = calendar.monthrange(year, end_month)[1]
            end_date = date(year, end_month, last_day)

        elif period_type == "Year":
            current_year = date.today().year
            years = [current_year - i for i in range(3)]
            selected_year = st.selectbox("Select Year", years)
            start_date = date(selected_year, 1, 1)
            end_date = date(selected_year, 12, 31)

        else:  # Custom
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
            end_date = st.date_input("End Date", value=date.today())

    with col3:
        st.metric(
            "Report Period",
            f"{(end_date - start_date).days} days",
            help="Length of the selected reporting period"
        )

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
        # Filter by date range
        if not revenue_df.empty:
            revenue_df = revenue_df[
                (pd.to_datetime(revenue_df["revenue_date"]) >= pd.to_datetime(start_date)) &
                (pd.to_datetime(revenue_df["revenue_date"]) <= pd.to_datetime(end_date))
            ]

        if not attribution_df.empty:
            attribution_df = attribution_df[
                (pd.to_datetime(attribution_df["revenue_date"]) >= pd.to_datetime(start_date)) &
                (pd.to_datetime(attribution_df["revenue_date"]) <= pd.to_datetime(end_date))
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
            st.metric(
                "Total Revenue",
                f"${total_revenue:,.0f}",
                delta=f"{dashboard_days}d period",
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
# TAB 1: DATA IMPORT (NEW)
# ============================================================================

with tabs[1]:
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
# TAB 2: RULE BUILDER (NEW)
# ============================================================================

with tabs[2]:
    st.title("⚙️ Rule Builder")
    st.caption("Create attribution rules using natural language, templates, or manual configuration")

    # ========================================
    # NATURAL LANGUAGE RULE CREATOR (HERO)
    # ========================================
    st.markdown("### ✨ Describe Your Attribution Model in Plain English")
    st.markdown('<p style="font-size: 0.9em; color: #6b7280; margin-top: -10px;">Powered by <b>Claude AI</b> — converts natural language to attribution rules instantly</p>', unsafe_allow_html=True)

    # Example prompts (clickable chips)
    st.markdown("**Try these examples:**")
    examples = get_example_prompts()

    # Create clickable example chips using columns
    example_cols = st.columns(2)

    if "nl_input_text" not in st.session_state:
        st.session_state.nl_input_text = ""

    with example_cols[0]:
        if st.button("📊 " + examples[0]["prompt"][:50] + "...", use_container_width=True):
            st.session_state.nl_input_text = examples[0]["prompt"]
            st.rerun()
        if st.button("📊 " + examples[1]["prompt"][:50] + "...", use_container_width=True):
            st.session_state.nl_input_text = examples[1]["prompt"]
            st.rerun()
        if st.button("📊 " + examples[2]["prompt"][:50] + "...", use_container_width=True):
            st.session_state.nl_input_text = examples[2]["prompt"]
            st.rerun()

    with example_cols[1]:
        if st.button("📊 " + examples[3]["prompt"][:50] + "...", use_container_width=True):
            st.session_state.nl_input_text = examples[3]["prompt"]
            st.rerun()
        if st.button("📊 " + examples[4]["prompt"][:50] + "...", use_container_width=True):
            st.session_state.nl_input_text = examples[4]["prompt"]
            st.rerun()
        if st.button("💡 See all 8 examples", use_container_width=True):
            with st.expander("📚 All Example Prompts", expanded=True):
                for ex in examples:
                    st.markdown(f"**{ex['description']}**")
                    st.code(ex["prompt"], language="text")
                    st.markdown("---")

    # Main NL input (large and prominent)
    nl_input = st.text_area(
        "Your attribution rule:",
        value=st.session_state.nl_input_text,
        placeholder="e.g., 'SI partners get 60%, Influence 30%, Referral 10%' or 'Give more credit to recent partner touches'",
        height=120,
        help="Describe how you want to split attribution among partners. Use plain English!"
    )

    # Parse button (prominent)
    parse_col1, parse_col2, parse_col3 = st.columns([2, 1, 2])

    with parse_col2:
        parse_clicked = st.button("🚀 Generate Rule", type="primary", use_container_width=True)

    if parse_clicked and nl_input:
        with st.spinner("🤖 AI is parsing your rule..."):
            success, rule_config, error = parse_nl_to_rule(nl_input)

            if success:
                st.success("✅ **Rule generated successfully!**")

                # Beautiful preview card
                st.markdown("---")
                st.markdown("### 📋 Generated Rule Configuration")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Rule Name:**")
                    st.info(rule_config['name'])

                    st.markdown(f"**Attribution Model:**")
                    st.info(rule_config['model_type'].replace('_', ' ').title())

                    st.markdown(f"**Split Constraint:**")
                    st.info(rule_config['split_constraint'].replace('_', ' ').title())

                with col2:
                    st.markdown(f"**Model Configuration:**")
                    st.json(rule_config['config'])

                # Show full JSON config in expander
                with st.expander("🔍 View Full JSON Configuration"):
                    st.json(rule_config)

                # Action buttons
                st.markdown("---")
                action_col1, action_col2, action_col3 = st.columns([1, 1, 2])

                with action_col1:
                    if st.button("💾 Save This Rule", type="primary", use_container_width=True):
                        new_rule = AttributionRule(
                            id=len(st.session_state.rules) + 1,
                            name=rule_config["name"],
                            model_type=AttributionModel(rule_config["model_type"]),
                            config=rule_config["config"],
                            split_constraint=SplitConstraint(rule_config["split_constraint"]),
                            applies_to=rule_config.get("applies_to", {}),
                            priority=100,
                            active=True
                        )
                        st.session_state.rules.append(new_rule)

                        # AUTO-RECALCULATE: Trigger attribution calculation with new rule
                        with st.spinner("💡 Recalculating attribution with new rule..."):
                            count = calculate_attribution_for_all_targets()

                        st.success(f"✅ Rule saved! Created {count} new ledger entries")
                        st.balloons()
                        st.rerun()

                with action_col2:
                    if st.button("✏️ Edit Manually", use_container_width=True):
                        st.info("👉 Use the 'Manual Config' tab below to modify the JSON configuration")

            else:
                st.error(f"❌ **Could not parse your rule**")
                st.markdown(f"**Error:** {error}")

                # Helpful suggestions
                st.markdown("**💡 Suggestions:**")
                st.markdown("""
- Try being more specific: "SI partners get 50%, Influence 30%, Referral 20%"
- Use keywords: "equal split", "first touch", "time decay", "activity based"
- Check the examples above for guidance
- Or use the Template Selection tab for pre-built rules
                """)

    elif parse_clicked and not nl_input:
        st.warning("⚠️ Please describe your attribution rule first!")

    st.markdown("---")

    # ========================================
    # ALTERNATIVE: TEMPLATES & MANUAL CONFIG
    # ========================================
    st.markdown("### 📚 Or Choose a Different Approach")

    builder_tabs = st.tabs(["Template Selection", "Manual Config"])

    # Template Selection sub-tab
    with builder_tabs[0]:
        st.markdown("### Choose from Prebuilt Templates")

        category = st.selectbox(
            "Category",
            ["industry", "deal_size", "maturity", "use_case", "base"],
            format_func=lambda x: x.replace("_", " ").title()
        )

        templates = list_templates(category)

        if templates:
            selected_template = st.selectbox(
                "Template",
                options=[t["id"] for t in templates],
                format_func=lambda tid: next((t["name"] for t in templates if t["id"] == tid), tid)
            )

            template_detail = get_template(selected_template)

            if template_detail:
                st.markdown("#### Template Details")
                st.markdown(f"**Name:** {template_detail['name']}")
                st.markdown(f"**Description:** {template_detail['description']}")
                st.markdown(f"**Model:** {template_detail['model_type']}")
                st.json(template_detail["config"])

                if st.button("Apply Template", type="primary"):
                    new_rule = AttributionRule(
                        id=len(st.session_state.rules) + 1,
                        name=template_detail["name"],
                        model_type=AttributionModel(template_detail["model_type"]),
                        config=template_detail["config"],
                        split_constraint=SplitConstraint(template_detail["split_constraint"]),
                        applies_to=template_detail.get("applies_to", {}),
                        priority=100,
                        active=True
                    )
                    st.session_state.rules.append(new_rule)
                    st.success(f"✅ Applied template: {template_detail['name']}")
                    st.rerun()

    # Manual Config sub-tab
    with builder_tabs[1]:
        st.markdown("### Manual Rule Configuration")
        st.caption("For advanced users who want full control over rule JSON")

        with st.form("manual_rule_form"):
            rule_name = st.text_input("Rule Name", value="Custom Rule")

            model_type = st.selectbox(
                "Attribution Model",
                options=[m.value for m in AttributionModel],
                format_func=lambda x: x.replace('_', ' ').title()
            )

            st.markdown("**Model Configuration (JSON):**")
            config_json = st.text_area(
                "Config",
                value='{"weights": {"Implementation (SI)": 0.5, "Influence": 0.3, "Referral": 0.2}}',
                height=150,
                help="Enter valid JSON configuration for the selected model"
            )

            priority = st.number_input("Priority", min_value=1, max_value=1000, value=100)

            if st.form_submit_button("Create Rule"):
                try:
                    config = json.loads(config_json)
                    new_rule = AttributionRule(
                        id=len(st.session_state.rules) + 1,
                        name=rule_name,
                        model_type=AttributionModel(model_type),
                        config=config,
                        split_constraint=SplitConstraint.MUST_SUM_TO_100,
                        applies_to={},
                        priority=priority,
                        active=True
                    )
                    st.session_state.rules.append(new_rule)
                    st.success(f"✅ Created rule: {rule_name}")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Error creating rule: {str(e)}")


# ============================================================================
# TAB 3: RULES & TEMPLATES (NEW)
# ============================================================================

with tabs[3]:
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
# TAB 4: DEAL DRILLDOWN (NEW)
# ============================================================================

with tabs[4]:
    st.title("💰 Deal Drilldown")
    st.caption("Detailed attribution breakdown for individual deals - perfect for partner dispute resolution")

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
                                key=f"override_{entry.partner_id}_{selected_target_id}",
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
# TAB 5: LEDGER EXPLORER (NEW)
# ============================================================================

with tabs[5]:
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
