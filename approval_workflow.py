"""
Approval Workflow for Partner Touchpoints
==========================================

Provides UI and logic for reviewing and approving partner-submitted touchpoints,
deal registrations, and self-reported activities.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import plotly.graph_objects as go

from models_new import PartnerTouchpoint, AttributionTarget, DataSource, TouchpointType
from session_manager import SessionManager


def render_approval_queue(session_mgr: SessionManager, current_user):
    """Render the approval queue for partner touchpoints."""

    st.title("📋 Approval Queue")
    st.caption("Review and approve partner-submitted touchpoints and deal registrations")

    # Get pending approvals
    pending_touchpoints = session_mgr.get_pending_approvals()

    if not pending_touchpoints:
        st.success("✅ No pending approvals")
        st.info("All partner submissions have been reviewed")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Pending Approvals",
            len(pending_touchpoints),
            help="Total touchpoints awaiting review"
        )

    with col2:
        deal_regs = [tp for tp in pending_touchpoints if tp.source == DataSource.DEAL_REGISTRATION]
        st.metric(
            "Deal Registrations",
            len(deal_regs),
            help="Partner-submitted deal registrations"
        )

    with col3:
        self_reported = [tp for tp in pending_touchpoints if tp.source == DataSource.PARTNER_PORTAL_REPORTING]
        st.metric(
            "Self-Reported Activities",
            len(self_reported),
            help="Partner-reported touchpoints"
        )

    st.markdown("---")

    # Filter options
    col1, col2 = st.columns(2)

    with col1:
        filter_type = st.selectbox(
            "Filter by Type",
            ["All", "Deal Registrations", "Self-Reported", "Marketplace", "Other"],
            key="approval_filter_type"
        )

    with col2:
        filter_partner = st.selectbox(
            "Filter by Partner",
            ["All"] + sorted(list(set([tp.partner_id for tp in pending_touchpoints]))),
            key="approval_filter_partner"
        )

    # Apply filters
    filtered_touchpoints = pending_touchpoints

    if filter_type != "All":
        if filter_type == "Deal Registrations":
            filtered_touchpoints = [tp for tp in filtered_touchpoints if tp.source == DataSource.DEAL_REGISTRATION]
        elif filter_type == "Self-Reported":
            filtered_touchpoints = [tp for tp in filtered_touchpoints if tp.source == DataSource.PARTNER_PORTAL_REPORTING]
        elif filter_type == "Marketplace":
            filtered_touchpoints = [tp for tp in filtered_touchpoints if tp.source == DataSource.MARKETPLACE_TRANSACTIONS]

    if filter_partner != "All":
        filtered_touchpoints = [tp for tp in filtered_touchpoints if tp.partner_id == filter_partner]

    st.markdown(f"### {len(filtered_touchpoints)} Touchpoint(s) to Review")

    # Render each touchpoint as a card
    for idx, touchpoint in enumerate(filtered_touchpoints):
        render_touchpoint_card(touchpoint, session_mgr, current_user, idx)


def render_touchpoint_card(touchpoint: PartnerTouchpoint, session_mgr: SessionManager, current_user, idx: int):
    """Render a single touchpoint approval card."""

    # Get the target (opportunity) for context
    target = None
    if touchpoint.target_id > 0:
        target = session_mgr.repo.get_target(touchpoint.target_id)

    # Get partner name
    partner_name = st.session_state.partners.get(touchpoint.partner_id, touchpoint.partner_id)

    # Determine card styling based on source
    if touchpoint.source == DataSource.DEAL_REGISTRATION:
        card_emoji = "🎯"
        card_color = "#667eea"
        source_label = "Deal Registration"
    elif touchpoint.source == DataSource.PARTNER_PORTAL_REPORTING:
        card_emoji = "📝"
        card_color = "#48bb78"
        source_label = "Self-Reported"
    elif touchpoint.source == DataSource.MARKETPLACE_TRANSACTIONS:
        card_emoji = "🏪"
        card_color = "#ed8936"
        source_label = "Marketplace"
    else:
        card_emoji = "📌"
        card_color = "#4299e1"
        source_label = touchpoint.source.value

    with st.expander(f"{card_emoji} **{partner_name}** - {source_label} - {touchpoint.role}", expanded=True):
        # Header info
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Partner:** {partner_name} (`{touchpoint.partner_id}`)")
            st.markdown(f"**Role:** {touchpoint.role}")
            st.markdown(f"**Source:** {source_label}")
            st.markdown(f"**Confidence:** {touchpoint.source_confidence:.0%}")

        with col2:
            if touchpoint.timestamp:
                days_ago = (datetime.now() - touchpoint.timestamp).days
                st.markdown(f"**Date:** {touchpoint.timestamp.strftime('%Y-%m-%d')}")
                st.caption(f"({days_ago} days ago)")

            if touchpoint.deal_reg_submitted_date:
                st.markdown(f"**Submitted:** {touchpoint.deal_reg_submitted_date.strftime('%Y-%m-%d')}")

        # Target/Opportunity info
        if target:
            st.markdown("---")
            st.markdown("### 💰 Associated Deal")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Name:** {target.name or target.external_id}")
            with col2:
                st.markdown(f"**Value:** ${target.value:,.0f}")
            with col3:
                st.markdown(f"**Type:** {target.type.value}")

        # Metadata details
        if touchpoint.metadata:
            st.markdown("---")
            st.markdown("### 📄 Additional Details")

            # Deal registration specific fields
            if touchpoint.source == DataSource.DEAL_REGISTRATION:
                if "estimated_value" in touchpoint.metadata:
                    st.markdown(f"**Estimated Value:** ${touchpoint.metadata['estimated_value']:,.0f}")
                if "expected_close_date" in touchpoint.metadata:
                    st.markdown(f"**Expected Close:** {touchpoint.metadata['expected_close_date']}")
                if "deal_stage" in touchpoint.metadata:
                    st.markdown(f"**Deal Stage:** {touchpoint.metadata['deal_stage']}")

            # Self-reported specific fields
            if touchpoint.source == DataSource.PARTNER_PORTAL_REPORTING:
                if "account_name" in touchpoint.metadata:
                    st.markdown(f"**Account:** {touchpoint.metadata['account_name']}")
                if "activity_type" in touchpoint.metadata:
                    st.markdown(f"**Activity Type:** {touchpoint.metadata['activity_type']}")
                if "description" in touchpoint.metadata:
                    st.markdown(f"**Description:**")
                    st.text(touchpoint.metadata['description'])
                if "submitted_by" in touchpoint.metadata:
                    st.caption(f"Submitted by: {touchpoint.metadata['submitted_by']}")

            # Show all other metadata
            other_metadata = {
                k: v for k, v in touchpoint.metadata.items()
                if k not in ['estimated_value', 'expected_close_date', 'deal_stage',
                           'account_name', 'activity_type', 'description', 'submitted_by']
            }
            if other_metadata:
                with st.expander("🔍 View All Metadata"):
                    st.json(other_metadata)

        # Approval actions
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button(
                "✅ Approve",
                key=f"approve_{touchpoint.id}_{idx}",
                type="primary",
                use_container_width=True
            ):
                # Approve touchpoint
                session_mgr.approve_touchpoint(
                    touchpoint.id,
                    approved_by=current_user.email
                )
                st.success(f"✅ Approved touchpoint from {partner_name}")
                st.rerun()

        with col2:
            if st.button(
                "❌ Reject",
                key=f"reject_{touchpoint.id}_{idx}",
                use_container_width=True
            ):
                # Show rejection reason input
                st.session_state[f"show_reject_reason_{touchpoint.id}"] = True

        # Rejection reason input (appears when reject button clicked)
        if st.session_state.get(f"show_reject_reason_{touchpoint.id}", False):
            with st.form(key=f"reject_form_{touchpoint.id}_{idx}"):
                st.markdown("**Rejection Reason:**")
                reason = st.text_area(
                    "Why are you rejecting this touchpoint?",
                    placeholder="E.g., Duplicate submission, Incorrect account, Insufficient evidence...",
                    key=f"reject_reason_{touchpoint.id}_{idx}",
                    label_visibility="collapsed"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Confirm Rejection", type="primary", use_container_width=True):
                        if reason:
                            session_mgr.reject_touchpoint(
                                touchpoint.id,
                                rejected_by=current_user.email,
                                reason=reason
                            )
                            st.success(f"❌ Rejected touchpoint from {partner_name}")
                            st.session_state[f"show_reject_reason_{touchpoint.id}"] = False
                            st.rerun()
                        else:
                            st.error("Please provide a rejection reason")

                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state[f"show_reject_reason_{touchpoint.id}"] = False
                        st.rerun()


def render_approval_history(session_mgr: SessionManager):
    """Render history of approved/rejected touchpoints."""

    st.title("📜 Approval History")
    st.caption("View all previously reviewed touchpoints")

    # Get all touchpoints (approved and rejected)
    all_touchpoints = session_mgr.get_all_touchpoints()

    # Filter to only those that have been reviewed
    reviewed_touchpoints = [
        tp for tp in all_touchpoints
        if tp.requires_approval and (tp.approved_by or tp.deal_reg_status == "rejected")
    ]

    if not reviewed_touchpoints:
        st.info("No approval history yet")
        return

    # Summary metrics
    approved = [tp for tp in reviewed_touchpoints if tp.approved_by]
    rejected = [tp for tp in reviewed_touchpoints if tp.deal_reg_status == "rejected"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Reviewed", len(reviewed_touchpoints))

    with col2:
        st.metric("Approved", len(approved), delta=None)

    with col3:
        st.metric("Rejected", len(rejected), delta=None)

    st.markdown("---")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Approved", "Rejected"],
            key="history_status_filter"
        )

    with col2:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            key="history_date_filter"
        )

    with col3:
        partner_filter = st.selectbox(
            "Partner",
            ["All"] + sorted(list(set([tp.partner_id for tp in reviewed_touchpoints]))),
            key="history_partner_filter"
        )

    # Apply filters
    filtered = reviewed_touchpoints

    if status_filter == "Approved":
        filtered = [tp for tp in filtered if tp.approved_by]
    elif status_filter == "Rejected":
        filtered = [tp for tp in filtered if tp.deal_reg_status == "rejected"]

    if partner_filter != "All":
        filtered = [tp for tp in filtered if tp.partner_id == partner_filter]

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = [
            tp for tp in filtered
            if tp.approval_timestamp and start_date <= tp.approval_timestamp.date() <= end_date
        ]

    # Build table
    history_data = []
    for tp in filtered:
        partner_name = st.session_state.partners.get(tp.partner_id, tp.partner_id)

        status = "✅ Approved" if tp.approved_by else "❌ Rejected"
        reviewed_by = tp.approved_by if tp.approved_by else tp.metadata.get('rejected_by', 'Unknown')
        reviewed_date = tp.approval_timestamp.strftime('%Y-%m-%d %H:%M') if tp.approval_timestamp else "N/A"

        rejection_reason = ""
        if tp.deal_reg_status == "rejected":
            rejection_reason = tp.metadata.get('rejection_reason', 'No reason provided')

        history_data.append({
            "Date": reviewed_date,
            "Partner": partner_name,
            "Role": tp.role,
            "Source": tp.source.value,
            "Status": status,
            "Reviewed By": reviewed_by,
            "Reason": rejection_reason if rejection_reason else "-"
        })

    if history_data:
        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Export History CSV",
            csv,
            "approval_history.csv",
            "text/csv",
            use_container_width=True
        )
    else:
        st.info("No records match the selected filters")

    # Approval timeline chart
    if len(history_data) > 0:
        st.markdown("---")
        st.markdown("### 📈 Approval Activity Over Time")

        df['Date_parsed'] = pd.to_datetime(df['Date'])
        df['Date_only'] = df['Date_parsed'].dt.date

        daily_counts = df.groupby('Date_only').size().reset_index(name='Count')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_counts['Date_only'],
            y=daily_counts['Count'],
            mode='lines+markers',
            name='Approvals',
            line=dict(color='#667eea', width=2),
            marker=dict(size=8)
        ))

        fig.update_layout(
            title="Daily Approval Activity",
            xaxis_title="Date",
            yaxis_title="Number of Reviews",
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)


def render_approval_stats(session_mgr: SessionManager):
    """Render approval workflow statistics and insights."""

    st.title("📊 Approval Workflow Statistics")
    st.caption("Insights into your approval process")

    # Get all touchpoints
    all_touchpoints = session_mgr.get_all_touchpoints()

    # Categorize
    requires_approval = [tp for tp in all_touchpoints if tp.requires_approval]
    pending = [tp for tp in requires_approval if not tp.approved_by and tp.deal_reg_status != "rejected"]
    approved = [tp for tp in requires_approval if tp.approved_by]
    rejected = [tp for tp in requires_approval if tp.deal_reg_status == "rejected"]

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Submissions", len(requires_approval))

    with col2:
        st.metric("Pending", len(pending))

    with col3:
        st.metric("Approved", len(approved))

    with col4:
        st.metric("Rejected", len(rejected))

    # Approval rate
    if len(requires_approval) > 0:
        approval_rate = len(approved) / len(requires_approval)
        st.markdown("---")
        st.markdown("### Approval Rate")
        st.progress(approval_rate, text=f"{approval_rate:.1%} of submissions approved")

    # Average time to approval
    approval_times = []
    for tp in approved:
        if tp.created_at and tp.approval_timestamp:
            time_diff = (tp.approval_timestamp - tp.created_at).total_seconds() / 3600  # hours
            approval_times.append(time_diff)

    if approval_times:
        avg_time = sum(approval_times) / len(approval_times)
        st.markdown("---")
        st.markdown("### Average Time to Approval")
        st.metric("Hours", f"{avg_time:.1f}")

    # Breakdown by source
    st.markdown("---")
    st.markdown("### Submissions by Source")

    source_counts = {}
    for tp in requires_approval:
        source = tp.source.value
        source_counts[source] = source_counts.get(source, 0) + 1

    if source_counts:
        fig = go.Figure(data=[go.Pie(
            labels=list(source_counts.keys()),
            values=list(source_counts.values()),
            hole=0.4
        )])

        fig.update_layout(
            title="Touchpoint Sources",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)
