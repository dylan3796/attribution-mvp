"""
Deal Registration Approval Workflow
====================================

Manages partner-submitted deal registrations with:
- Approval/rejection workflow
- Expiry logic (90-day default)
- Conflict detection (duplicate submissions)
- Status tracking (pending, approved, rejected, expired)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

from models_new import PartnerTouchpoint, AttributionTarget, TouchpointType, DataSource


# ============================================================================
# Deal Registration Status
# ============================================================================

class DealRegStatus(str, Enum):
    """Deal registration workflow statuses."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"


# ============================================================================
# Deal Registration Object
# ============================================================================

@dataclass
class DealRegistration:
    """Represents a partner-submitted deal registration."""

    id: int
    partner_id: str
    partner_name: str

    # Deal details
    opportunity_name: str
    estimated_value: float
    expected_close_date: datetime
    account_name: str
    description: str

    # Workflow
    status: DealRegStatus = DealRegStatus.PENDING
    submitted_date: datetime = field(default_factory=datetime.now)
    approved_date: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejected_date: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Expiry
    expiry_days: int = 90
    expires_at: Optional[datetime] = None

    # Salesforce linkage
    opportunity_id: Optional[str] = None  # Once approved, link to SFDC opp

    # Metadata
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Calculate expiry date."""
        if not self.expires_at:
            self.expires_at = self.submitted_date + timedelta(days=self.expiry_days)

    def is_expired(self) -> bool:
        """Check if deal reg has expired."""
        return datetime.now() > self.expires_at and self.status == DealRegStatus.PENDING

    def days_until_expiry(self) -> int:
        """Days remaining until expiry."""
        if self.status != DealRegStatus.PENDING:
            return 0
        days = (self.expires_at - datetime.now()).days
        return max(0, days)

    def to_touchpoint(self, target_id: int = 0) -> PartnerTouchpoint:
        """Convert to PartnerTouchpoint for attribution."""
        return PartnerTouchpoint(
            id=self.id,
            partner_id=self.partner_id,
            target_id=target_id,
            touchpoint_type=TouchpointType.DEAL_REGISTRATION,
            role="Referral",
            weight=1.0,
            timestamp=self.submitted_date,
            source=DataSource.DEAL_REGISTRATION,
            source_id=str(self.id),
            source_confidence=1.0,  # Approved deal reg = definitive
            deal_reg_status=self.status.value,
            deal_reg_submitted_date=self.submitted_date,
            requires_approval=True,
            approved_by=self.approved_by,
            approval_timestamp=self.approved_date,
            metadata={
                "opportunity_name": self.opportunity_name,
                "estimated_value": self.estimated_value,
                "expected_close_date": self.expected_close_date.isoformat(),
                "account_name": self.account_name,
                "description": self.description,
                "expires_at": self.expires_at.isoformat(),
                "days_until_expiry": self.days_until_expiry()
            }
        )


# ============================================================================
# Deal Registration Manager
# ============================================================================

class DealRegistrationManager:
    """Manages deal registration lifecycle and approval workflow."""

    def __init__(self, expiry_days: int = 90):
        self.expiry_days = expiry_days

    def submit_deal_registration(
        self,
        partner_id: str,
        partner_name: str,
        opportunity_name: str,
        estimated_value: float,
        expected_close_date: datetime,
        account_name: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> DealRegistration:
        """Partner submits new deal registration."""

        deal_reg = DealRegistration(
            id=0,  # Will be assigned by DB
            partner_id=partner_id,
            partner_name=partner_name,
            opportunity_name=opportunity_name,
            estimated_value=estimated_value,
            expected_close_date=expected_close_date,
            account_name=account_name,
            description=description,
            status=DealRegStatus.PENDING,
            submitted_date=datetime.now(),
            expiry_days=self.expiry_days,
            metadata=metadata or {}
        )

        return deal_reg

    def approve_deal_registration(
        self,
        deal_reg: DealRegistration,
        approved_by: str,
        opportunity_id: Optional[str] = None
    ) -> DealRegistration:
        """Approve pending deal registration."""

        if deal_reg.status != DealRegStatus.PENDING:
            raise ValueError(f"Cannot approve deal reg with status: {deal_reg.status}")

        if deal_reg.is_expired():
            deal_reg.status = DealRegStatus.EXPIRED
            raise ValueError("Cannot approve expired deal registration")

        deal_reg.status = DealRegStatus.APPROVED
        deal_reg.approved_date = datetime.now()
        deal_reg.approved_by = approved_by
        deal_reg.opportunity_id = opportunity_id

        return deal_reg

    def reject_deal_registration(
        self,
        deal_reg: DealRegistration,
        rejected_by: str,
        reason: str
    ) -> DealRegistration:
        """Reject pending deal registration."""

        if deal_reg.status != DealRegStatus.PENDING:
            raise ValueError(f"Cannot reject deal reg with status: {deal_reg.status}")

        deal_reg.status = DealRegStatus.REJECTED
        deal_reg.rejected_date = datetime.now()
        deal_reg.rejected_by = rejected_by
        deal_reg.rejection_reason = reason

        return deal_reg

    def detect_duplicates(
        self,
        deal_reg: DealRegistration,
        existing_deal_regs: List[DealRegistration]
    ) -> List[DealRegistration]:
        """Detect duplicate deal registrations."""

        duplicates = []

        for existing in existing_deal_regs:
            # Skip self
            if existing.id == deal_reg.id:
                continue

            # Skip rejected/expired
            if existing.status in [DealRegStatus.REJECTED, DealRegStatus.EXPIRED]:
                continue

            # Check for duplicates
            is_duplicate = (
                existing.account_name.lower() == deal_reg.account_name.lower()
                and existing.opportunity_name.lower() == deal_reg.opportunity_name.lower()
                and abs((existing.expected_close_date - deal_reg.expected_close_date).days) <= 30
            )

            if is_duplicate:
                duplicates.append(existing)

        return duplicates

    def expire_old_registrations(
        self,
        deal_regs: List[DealRegistration]
    ) -> List[DealRegistration]:
        """Mark expired deal registrations."""

        expired = []

        for deal_reg in deal_regs:
            if deal_reg.is_expired():
                deal_reg.status = DealRegStatus.EXPIRED
                expired.append(deal_reg)

        return expired

    def get_pending_registrations(
        self,
        deal_regs: List[DealRegistration],
        expiring_soon_days: int = 7
    ) -> Dict[str, List[DealRegistration]]:
        """Get pending registrations grouped by urgency."""

        pending = [dr for dr in deal_regs if dr.status == DealRegStatus.PENDING and not dr.is_expired()]

        expiring_soon = [dr for dr in pending if dr.days_until_expiry() <= expiring_soon_days]
        normal = [dr for dr in pending if dr.days_until_expiry() > expiring_soon_days]

        return {
            "expiring_soon": expiring_soon,
            "normal": normal
        }


# ============================================================================
# Deal Registration UI Components
# ============================================================================

def render_deal_reg_approval_queue(
    deal_regs: List[DealRegistration],
    on_approve_callback,
    on_reject_callback
):
    """Render approval queue UI (Streamlit component)."""
    import streamlit as st
    import pandas as pd

    st.markdown("### 📋 Deal Registration Approval Queue")

    # Get pending registrations
    manager = DealRegistrationManager()
    pending_groups = manager.get_pending_registrations(deal_regs)

    expiring_soon = pending_groups["expiring_soon"]
    normal = pending_groups["normal"]

    # Expiring soon (urgent)
    if expiring_soon:
        st.error(f"⚠️ **{len(expiring_soon)} deal registration(s) expiring soon!**")

        for deal_reg in expiring_soon:
            with st.expander(f"🚨 {deal_reg.opportunity_name} - Expires in {deal_reg.days_until_expiry()} days"):
                render_deal_reg_card(deal_reg, on_approve_callback, on_reject_callback)

    # Normal pending
    if normal:
        st.info(f"📥 {len(normal)} pending deal registration(s)")

        for deal_reg in normal:
            with st.expander(f"{deal_reg.opportunity_name} - {deal_reg.partner_name}"):
                render_deal_reg_card(deal_reg, on_approve_callback, on_reject_callback)

    # No pending
    if not expiring_soon and not normal:
        st.success("✅ No pending deal registrations")


def render_deal_reg_card(
    deal_reg: DealRegistration,
    on_approve_callback,
    on_reject_callback
):
    """Render individual deal registration card."""
    import streamlit as st

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Partner:** {deal_reg.partner_name}")
        st.markdown(f"**Account:** {deal_reg.account_name}")
        st.markdown(f"**Estimated Value:** ${deal_reg.estimated_value:,.0f}")
        st.markdown(f"**Expected Close:** {deal_reg.expected_close_date.strftime('%Y-%m-%d')}")

    with col2:
        st.markdown(f"**Submitted:** {deal_reg.submitted_date.strftime('%Y-%m-%d')}")
        st.markdown(f"**Expires:** {deal_reg.expires_at.strftime('%Y-%m-%d')}")
        st.markdown(f"**Days Remaining:** {deal_reg.days_until_expiry()}")

    st.markdown("---")
    st.markdown(f"**Description:**")
    st.markdown(deal_reg.description)

    st.markdown("---")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        opportunity_id = st.text_input(
            "Link to Salesforce Opportunity (optional)",
            placeholder="Opportunity ID",
            key=f"opp_id_{deal_reg.id}"
        )

    with col2:
        if st.button("✅ Approve", type="primary", key=f"approve_{deal_reg.id}", width='stretch'):
            on_approve_callback(deal_reg, opportunity_id)

    with col3:
        if st.button("❌ Reject", type="secondary", key=f"reject_{deal_reg.id}", width='stretch'):
            # Show rejection reason modal
            st.session_state[f"rejecting_{deal_reg.id}"] = True

    # Rejection reason modal
    if st.session_state.get(f"rejecting_{deal_reg.id}"):
        with st.form(f"reject_form_{deal_reg.id}"):
            reason = st.text_area("Rejection Reason", height=100)
            col1, col2 = st.columns(2)

            with col1:
                if st.form_submit_button("Confirm Rejection", width='stretch'):
                    on_reject_callback(deal_reg, reason)
                    st.session_state[f"rejecting_{deal_reg.id}"] = False
                    st.rerun()

            with col2:
                if st.form_submit_button("Cancel", width='stretch'):
                    st.session_state[f"rejecting_{deal_reg.id}"] = False
                    st.rerun()
