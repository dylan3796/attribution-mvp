"""
Period Management for Attribution Calculations
==============================================

Provides UI and logic for managing attribution periods (monthly, quarterly, annual).
Enables closing periods for reporting and locking historical data.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from calendar import monthrange
import plotly.graph_objects as go

from models import AttributionPeriod, PeriodType, PeriodStatus
from session_manager import SessionManager


def render_period_management(session_mgr: SessionManager, current_user):
    """Main period management interface."""

    st.title("📅 Period Management")
    st.caption("Manage attribution periods, close reporting periods, and lock historical data")

    # Sub-tabs
    sub_tabs = st.tabs([
        "📋 All Periods",
        "➕ Create Period",
        "📊 Period Analytics"
    ])

    with sub_tabs[0]:
        render_period_list(session_mgr, current_user)

    with sub_tabs[1]:
        render_create_period(session_mgr, current_user)

    with sub_tabs[2]:
        render_period_analytics(session_mgr)


def render_period_list(session_mgr: SessionManager, current_user):
    """Display list of all attribution periods."""

    st.markdown("### All Attribution Periods")

    # Get all periods
    periods = session_mgr.repo.get_all_periods(current_user.organization_id)

    if not periods:
        st.info("📭 No periods created yet")
        st.markdown("Create your first attribution period using the **Create Period** tab.")
        return

    # Filter options
    col1, col2 = st.columns(2)

    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Open", "Closed", "Locked"],
            key="period_status_filter"
        )

    with col2:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All", "Monthly", "Quarterly", "Annual", "Custom"],
            key="period_type_filter"
        )

    # Apply filters
    filtered_periods = periods

    if status_filter != "All":
        status_enum = PeriodStatus[status_filter.upper()]
        filtered_periods = [p for p in filtered_periods if p.status == status_enum]

    if type_filter != "All":
        type_enum = PeriodType[type_filter.upper()]
        filtered_periods = [p for p in filtered_periods if p.period_type == type_enum]

    # Sort by start date (newest first)
    filtered_periods.sort(key=lambda p: p.start_date, reverse=True)

    st.markdown(f"**{len(filtered_periods)} Period(s)**")
    st.markdown("---")

    # Render each period as a card
    for period in filtered_periods:
        render_period_card(period, session_mgr, current_user)


def render_period_card(period: AttributionPeriod, session_mgr: SessionManager, current_user):
    """Render a single period card with actions."""

    # Status styling
    if period.is_locked():
        status_emoji = "🔒"
        status_color = "#e53e3e"
        status_label = "Locked"
    elif period.is_closed():
        status_emoji = "✅"
        status_color = "#48bb78"
        status_label = "Closed"
    else:
        status_emoji = "🟢"
        status_color = "#4299e1"
        status_label = "Open"

    # Type styling
    type_icons = {
        PeriodType.MONTHLY: "📅",
        PeriodType.QUARTERLY: "📆",
        PeriodType.ANNUAL: "🗓️",
        PeriodType.CUSTOM: "🔧"
    }
    type_emoji = type_icons.get(period.period_type, "📋")

    with st.expander(
        f"{type_emoji} **{period.name}** {status_emoji} {status_label}",
        expanded=period.is_open()
    ):
        # Header info
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"**Type:** {period.period_type.value.title()}")
            st.markdown(f"**Status:** {status_label}")

        with col2:
            st.markdown(f"**Start Date:** {period.start_date.strftime('%Y-%m-%d')}")
            st.markdown(f"**End Date:** {period.end_date.strftime('%Y-%m-%d')}")

        with col3:
            duration = (period.end_date - period.start_date).days
            st.markdown(f"**Duration:** {duration} days")
            if period.created_by:
                st.markdown(f"**Created By:** {period.created_by}")

        # Summary statistics (if closed)
        if period.is_closed():
            st.markdown("---")
            st.markdown("### 📊 Period Summary")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total Revenue",
                    f"${period.total_revenue:,.0f}",
                    help="Total attributed revenue in this period"
                )

            with col2:
                st.metric(
                    "Total Deals",
                    f"{period.total_deals:,}",
                    help="Number of deals closed in this period"
                )

            with col3:
                st.metric(
                    "Active Partners",
                    f"{period.total_partners:,}",
                    help="Number of partners with attribution in this period"
                )

            # Close/lock metadata
            if period.closed_at:
                st.caption(f"Closed on {period.closed_at.strftime('%Y-%m-%d %H:%M')} by {period.closed_by}")

            if period.locked_at:
                st.caption(f"🔒 Locked on {period.locked_at.strftime('%Y-%m-%d %H:%M')} by {period.locked_by}")

        # Notes
        if period.notes:
            st.markdown("---")
            st.markdown("**Notes:**")
            st.text(period.notes)

        # Actions
        st.markdown("---")
        render_period_actions(period, session_mgr, current_user)


def render_period_actions(period: AttributionPeriod, session_mgr: SessionManager, current_user):
    """Render action buttons for a period based on its status."""

    # Only admins and managers can modify periods
    is_authorized = current_user.role.value in ["admin", "manager"]

    if not is_authorized:
        st.caption("🔒 Period actions require Admin or Manager role")
        return

    if period.is_open():
        # Open period actions
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "📊 Close Period",
                key=f"close_period_{period.id}",
                help="Close this period and calculate summary statistics",
                use_container_width=True
            ):
                # Calculate summary statistics
                summary = calculate_period_summary(period, session_mgr)

                # Close the period
                session_mgr.repo.close_period(
                    period_id=period.id,
                    closed_by=current_user.email,
                    total_revenue=summary["total_revenue"],
                    total_deals=summary["total_deals"],
                    total_partners=summary["total_partners"]
                )

                st.success(f"✅ Closed period: {period.name}")
                st.rerun()

        with col2:
            if st.button(
                "🗑️ Delete Period",
                key=f"delete_period_{period.id}",
                help="Permanently delete this period",
                use_container_width=True
            ):
                session_mgr.repo.delete_period(period.id)
                st.success(f"🗑️ Deleted period: {period.name}")
                st.rerun()

    elif period.is_closed() and not period.is_locked():
        # Closed period actions
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(
                "🔒 Lock Period",
                key=f"lock_period_{period.id}",
                help="Lock this period to prevent any future changes",
                type="primary",
                use_container_width=True
            ):
                session_mgr.repo.lock_period(
                    period_id=period.id,
                    locked_by=current_user.email
                )
                st.success(f"🔒 Locked period: {period.name}")
                st.rerun()

        with col2:
            if st.button(
                "🔄 Recalculate",
                key=f"recalc_period_{period.id}",
                help="Recalculate summary statistics",
                use_container_width=True
            ):
                # Recalculate summary
                summary = calculate_period_summary(period, session_mgr)

                # Update the period
                session_mgr.repo.close_period(
                    period_id=period.id,
                    closed_by=current_user.email,
                    total_revenue=summary["total_revenue"],
                    total_deals=summary["total_deals"],
                    total_partners=summary["total_partners"]
                )

                st.success(f"🔄 Recalculated period: {period.name}")
                st.rerun()

        with col3:
            if st.button(
                "🔓 Reopen Period",
                key=f"reopen_period_{period.id}",
                help="Reopen this period for changes",
                use_container_width=True
            ):
                session_mgr.repo.reopen_period(period.id)
                st.success(f"🔓 Reopened period: {period.name}")
                st.rerun()

    elif period.is_locked():
        # Locked period - very limited actions
        st.warning("🔒 This period is locked and cannot be modified")

        if current_user.role.value == "admin":
            if st.button(
                "⚠️ Force Unlock (Admin Only)",
                key=f"unlock_period_{period.id}",
                help="Unlock this period (admin only - use with caution)",
                use_container_width=True
            ):
                session_mgr.repo.reopen_period(period.id)
                st.success(f"🔓 Force unlocked period: {period.name}")
                st.rerun()


def render_create_period(session_mgr: SessionManager, current_user):
    """Form to create a new attribution period."""

    st.markdown("### Create New Period")

    # Only admins and managers can create periods
    if current_user.role.value not in ["admin", "manager"]:
        st.error("🔒 Access Denied")
        st.warning("You need Admin or Manager role to create periods.")
        return

    with st.form("create_period_form"):
        # Period type
        period_type = st.selectbox(
            "Period Type",
            options=list(PeriodType),
            format_func=lambda x: x.value.title(),
            help="Select the type of period to create"
        )

        # Quick create templates
        st.markdown("#### Quick Templates")
        col1, col2, col3 = st.columns(3)

        with col1:
            use_current_month = st.checkbox(
                "Current Month",
                help="Create period for current month"
            )

        with col2:
            use_current_quarter = st.checkbox(
                "Current Quarter",
                help="Create period for current quarter"
            )

        with col3:
            use_current_year = st.checkbox(
                "Current Year",
                help="Create period for current year"
            )

        # Auto-fill dates based on template
        today = date.today()

        if use_current_month:
            start_date_default = today.replace(day=1)
            last_day = monthrange(today.year, today.month)[1]
            end_date_default = today.replace(day=last_day)
            name_default = f"{today.strftime('%B %Y')}"
        elif use_current_quarter:
            quarter = (today.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date_default = today.replace(month=start_month, day=1)
            end_month = start_month + 2
            last_day = monthrange(today.year, end_month)[1]
            end_date_default = today.replace(month=end_month, day=last_day)
            name_default = f"Q{quarter} {today.year}"
        elif use_current_year:
            start_date_default = today.replace(month=1, day=1)
            end_date_default = today.replace(month=12, day=31)
            name_default = f"FY {today.year}"
        else:
            start_date_default = today.replace(day=1)
            last_day = monthrange(today.year, today.month)[1]
            end_date_default = today.replace(day=last_day)
            name_default = f"{today.strftime('%B %Y')}"

        st.markdown("---")

        # Period details
        name = st.text_input(
            "Period Name",
            value=name_default,
            help="Descriptive name for this period (e.g., 'Q1 2024', 'January 2024')"
        )

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Start Date",
                value=start_date_default,
                help="First day of the attribution period"
            )

        with col2:
            end_date = st.date_input(
                "End Date",
                value=end_date_default,
                help="Last day of the attribution period"
            )

        notes = st.text_area(
            "Notes (Optional)",
            placeholder="Add any notes about this period...",
            help="Optional notes or context for this period"
        )

        # Submit button
        submitted = st.form_submit_button(
            "✅ Create Period",
            type="primary",
            use_container_width=True
        )

        if submitted:
            # Validation
            if not name:
                st.error("Please provide a period name")
            elif start_date >= end_date:
                st.error("End date must be after start date")
            else:
                # Create period
                period = AttributionPeriod(
                    id=0,  # Will be set by database
                    organization_id=current_user.organization_id,
                    name=name,
                    period_type=period_type,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time()),
                    status=PeriodStatus.OPEN,
                    created_by=current_user.email,
                    notes=notes if notes else None
                )

                period_id = session_mgr.repo.create_period(period)

                st.success(f"✅ Created period: {name}")
                st.info(f"Period ID: {period_id}")
                st.balloons()

                # Clear form by rerunning
                st.rerun()


def render_period_analytics(session_mgr: SessionManager):
    """Display analytics across all periods."""

    st.markdown("### Period Analytics")

    # Get all periods
    periods = session_mgr.repo.get_all_periods(st.session_state.current_user.organization_id)

    if not periods:
        st.info("📭 No periods to analyze yet")
        return

    # Filter to closed periods only
    closed_periods = [p for p in periods if p.is_closed()]

    if not closed_periods:
        st.info("📊 No closed periods yet - close a period to see analytics")
        return

    # Summary metrics
    total_revenue = sum(p.total_revenue for p in closed_periods)
    total_deals = sum(p.total_deals for p in closed_periods)
    avg_period_revenue = total_revenue / len(closed_periods) if closed_periods else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Periods",
            len(closed_periods),
            help="Number of closed attribution periods"
        )

    with col2:
        st.metric(
            "Total Revenue",
            f"${total_revenue:,.0f}",
            help="Sum of all closed period revenue"
        )

    with col3:
        st.metric(
            "Total Deals",
            f"{total_deals:,}",
            help="Sum of all closed period deals"
        )

    with col4:
        st.metric(
            "Avg Period Revenue",
            f"${avg_period_revenue:,.0f}",
            help="Average revenue per closed period"
        )

    st.markdown("---")

    # Revenue trend chart
    st.markdown("### 📈 Revenue Trend by Period")

    # Sort periods by start date
    sorted_periods = sorted(closed_periods, key=lambda p: p.start_date)

    # Build chart data
    period_names = [p.name for p in sorted_periods]
    period_revenues = [p.total_revenue for p in sorted_periods]
    period_deals = [p.total_deals for p in sorted_periods]

    # Create dual-axis chart
    fig = go.Figure()

    # Revenue bars
    fig.add_trace(go.Bar(
        x=period_names,
        y=period_revenues,
        name="Revenue",
        marker_color="#667eea",
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>"
    ))

    # Deal count line
    fig.add_trace(go.Scatter(
        x=period_names,
        y=period_deals,
        name="Deals",
        mode="lines+markers",
        marker=dict(size=10, color="#48bb78"),
        line=dict(width=3, color="#48bb78"),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Deals: %{y}<extra></extra>"
    ))

    fig.update_layout(
        title="Revenue and Deals by Period",
        xaxis_title="Period",
        yaxis=dict(
            title="Revenue ($)",
            titlefont=dict(color="#667eea"),
            tickfont=dict(color="#667eea")
        ),
        yaxis2=dict(
            title="Number of Deals",
            titlefont=dict(color="#48bb78"),
            tickfont=dict(color="#48bb78"),
            overlaying="y",
            side="right"
        ),
        hovermode="x unified",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Period comparison table
    st.markdown("### 📊 Period Comparison")

    comparison_data = []
    for p in sorted_periods:
        avg_deal_size = p.total_revenue / p.total_deals if p.total_deals > 0 else 0

        comparison_data.append({
            "Period": p.name,
            "Type": p.period_type.value.title(),
            "Revenue": f"${p.total_revenue:,.0f}",
            "Deals": p.total_deals,
            "Partners": p.total_partners,
            "Avg Deal Size": f"${avg_deal_size:,.0f}",
            "Status": "🔒 Locked" if p.is_locked() else "✅ Closed"
        })

    if comparison_data:
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export button
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Export Period Data CSV",
            csv,
            "period_comparison.csv",
            "text/csv",
            use_container_width=True
        )


def calculate_period_summary(period: AttributionPeriod, session_mgr: SessionManager) -> Dict[str, float]:
    """
    Calculate summary statistics for a period.

    Returns:
        Dict with total_revenue, total_deals, total_partners
    """
    # Get all ledger entries in this period
    all_entries = session_mgr.repo.get_all_ledger_entries()

    # Filter to period date range
    period_entries = [
        entry for entry in all_entries
        if period.contains_date(entry.timestamp)
    ]

    if not period_entries:
        return {
            "total_revenue": 0.0,
            "total_deals": 0,
            "total_partners": 0
        }

    # Calculate totals
    total_revenue = sum(entry.attributed_value for entry in period_entries)

    # Count unique deals
    unique_targets = set(entry.target_id for entry in period_entries)
    total_deals = len(unique_targets)

    # Count unique partners
    unique_partners = set(entry.partner_id for entry in period_entries)
    total_partners = len(unique_partners)

    return {
        "total_revenue": total_revenue,
        "total_deals": total_deals,
        "total_partners": total_partners
    }
