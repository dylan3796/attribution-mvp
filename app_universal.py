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

# Preserve original dashboard visualizations
from dashboards import (
    create_revenue_over_time_chart,
    create_partner_performance_bar_chart,
    create_attribution_pie_chart,
    create_pipeline_funnel_chart,
    create_partner_role_distribution,
    create_attribution_waterfall
)
from exports import export_to_csv, export_to_excel, generate_pdf_report

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
    "🔍 Ledger Explorer"
])


# ============================================================================
# TAB 0: DASHBOARD (PRESERVED FROM ORIGINAL)
# ============================================================================

with tabs[0]:
    st.title("Attribution Dashboard")
    st.caption("Executive overview of partner attribution performance and metrics")

    # Date range selector (preserved from original)
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        dashboard_days = st.selectbox(
            "Time Period",
            [7, 30, 60, 90, 180],
            index=1,
            format_func=lambda x: f"Last {x} days"
        )
    with col2:
        if st.button("Refresh Dashboard", type="primary"):
            st.rerun()

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=dashboard_days)

    # Get data using new architecture
    revenue_df = get_revenue_as_dataframe()
    attribution_df = get_ledger_as_dataframe()

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
            delta=f"{dashboard_days}d period"
        )

    with metric_cols[1]:
        st.metric(
            "Attributed Revenue",
            f"${total_attributed:,.0f}",
            delta=f"{attribution_coverage:.1f}% coverage"
        )

    with metric_cols[2]:
        unique_accounts = revenue_df["account_id"].nunique() if not revenue_df.empty else 0
        st.metric(
            "Active Accounts",
            f"{unique_accounts}",
            delta=f"{len(st.session_state.targets)} targets"
        )

    with metric_cols[3]:
        unique_partners = attribution_agg["partner_id"].nunique() if not attribution_agg.empty else 0
        st.metric(
            "Partner Count",
            f"{len(st.session_state.partners)}",
            delta=f"{unique_partners} active"
        )

    with metric_cols[4]:
        st.metric(
            "Touchpoints",
            f"{len(st.session_state.touchpoints)}",
            delta=f"{len(st.session_state.ledger)} ledger entries"
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

    # Attribution Waterfall (PRESERVED)
    st.markdown("### Attribution Breakdown")
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
            pdf_data = generate_pdf_report(
                title="Partner Performance Report",
                summary_data={
                    "Report Period": f"{start_date} to {end_date}",
                    "Total Revenue": total_revenue,
                    "Attributed Revenue": total_attributed,
                    "Attribution Coverage": f"{attribution_coverage:.1f}%",
                    "Active Partners": unique_partners
                },
                tables={
                    "Partner Performance": attribution_agg[["partner_name", "attributed_amount", "accounts_influenced"]].head(10)
                }
            )
            st.download_button(
                "Download PDF Report",
                data=pdf_data,
                file_name=f"attribution_report_{end_date}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    # Top Partners Table (PRESERVED)
    st.markdown("---")
    st.markdown("### Top 10 Partners by Attributed Revenue")
    if not attribution_agg.empty:
        top_10 = attribution_agg.nlargest(10, "attributed_amount")
        st.dataframe(
            top_10[["partner_name", "attributed_amount", "avg_split_percent", "accounts_influenced"]],
            use_container_width=True
        )


# ============================================================================
# TAB 1: DATA IMPORT (NEW)
# ============================================================================

with tabs[1]:
    st.title("📥 Data Import")
    st.caption("Upload CSV data with automatic schema detection")

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
            if st.button("Import Data", type="primary"):
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

            if st.form_submit_button("Add Entry", type="primary"):
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
    st.caption("Create attribution rules using templates or natural language")

    builder_tabs = st.tabs(["Natural Language", "Template Selection", "Manual Config"])

    # Natural Language sub-tab
    with builder_tabs[0]:
        st.markdown("### Create Rule from Natural Language")

        # Show examples
        with st.expander("💡 Example Prompts"):
            examples = get_example_prompts()
            for ex in examples[:5]:
                st.code(ex["prompt"], language="text")

        nl_input = st.text_area(
            "Describe your attribution rule in plain English:",
            placeholder="e.g., 'SI partners get 60%, Influence 30%, Referral 10%'",
            height=100
        )

        if st.button("Parse Rule", type="primary"):
            if nl_input:
                success, rule_config, error = parse_nl_to_rule(nl_input)

                if success:
                    st.success("✅ Parsed successfully!")
                    st.json(rule_config)

                    # Preview
                    st.markdown("#### Preview")
                    st.markdown(f"**Name:** {rule_config['name']}")
                    st.markdown(f"**Model:** {rule_config['model_type']}")
                    st.markdown(f"**Config:** `{rule_config['config']}`")

                    if st.button("Save Rule"):
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
                        st.success("Rule saved!")
                        st.rerun()
                else:
                    st.error(f"❌ {error}")

    # Template Selection sub-tab
    with builder_tabs[1]:
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
# TAB 4: LEDGER EXPLORER (NEW)
# ============================================================================

with tabs[4]:
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
