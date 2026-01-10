"""
Test Suite for Measurement Workflows
====================================

Tests the multi-source attribution workflow system including:
- Priority-based source selection
- Weighted merge of sources
- Fallback strategies
- Source filtering
- End-to-end workflow execution
"""

import pytest
from datetime import datetime, timedelta
from models import (
    AttributionTarget,
    PartnerTouchpoint,
    AttributionRule,
    AttributionModel,
    SplitConstraint,
    DataSource,
    DataSourceConfig,
    MeasurementWorkflow,
    TouchpointType,
    TargetType
)
from attribution_engine import AttributionEngine


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_target():
    """Create a sample attribution target (opportunity)."""
    return AttributionTarget(
        id=1,
        type=TargetType.OPPORTUNITY,
        external_id="OPP-001",
        value=100000.0,
        timestamp=datetime(2025, 1, 15),
        metadata={"account_name": "Acme Corp", "stage": "Closed Won"}
    )


@pytest.fixture
def deal_reg_touchpoint():
    """Create a deal registration touchpoint."""
    return PartnerTouchpoint(
        id=1,
        partner_id="P001",
        target_id=1,
        touchpoint_type=TouchpointType.DEAL_REGISTRATION,
        role="Referral",
        weight=1.0,
        timestamp=datetime(2024, 12, 1),
        source=DataSource.DEAL_REGISTRATION,
        source_id="DR-123",
        source_confidence=1.0,
        deal_reg_status="approved"
    )


@pytest.fixture
def touchpoint_tracking():
    """Create standard touchpoint tracking touchpoints."""
    return [
        PartnerTouchpoint(
            id=2,
            partner_id="P002",
            target_id=1,
            touchpoint_type=TouchpointType.ACTIVITY,
            role="Implementation (SI)",
            weight=5.0,
            timestamp=datetime(2024, 12, 15),
            source=DataSource.TOUCHPOINT_TRACKING,
            source_confidence=1.0
        ),
        PartnerTouchpoint(
            id=3,
            partner_id="P003",
            target_id=1,
            touchpoint_type=TouchpointType.ACTIVITY,
            role="Influence",
            weight=3.0,
            timestamp=datetime(2024, 12, 20),
            source=DataSource.TOUCHPOINT_TRACKING,
            source_confidence=1.0
        )
    ]


@pytest.fixture
def role_weighted_rule():
    """Create a role-weighted attribution rule."""
    return AttributionRule(
        id=1,
        name="Role Weighted",
        model_type=AttributionModel.ROLE_WEIGHTED,
        config={"weights": {"Implementation (SI)": 0.6, "Influence": 0.3, "Referral": 0.1}},
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        active=True
    )


# ============================================================================
# Priority Selection Tests
# ============================================================================

def test_priority_selection_deal_reg_wins(sample_target, deal_reg_touchpoint, touchpoint_tracking, role_weighted_rule):
    """
    Test that deal reg is selected when it has higher priority.

    Workflow: Priority 1 = Deal Reg, Priority 2 = Touchpoints
    Expected: Use deal reg touchpoint only
    """
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Deal Reg Primary",
        description="Test workflow",
        data_sources=[
            DataSourceConfig(
                source_type=DataSource.DEAL_REGISTRATION,
                priority=1,
                enabled=True
            ),
            DataSourceConfig(
                source_type=DataSource.TOUCHPOINT_TRACKING,
                priority=2,
                enabled=True
            )
        ],
        conflict_resolution="priority",
        fallback_strategy="next_priority"
    )

    all_touchpoints = [deal_reg_touchpoint] + touchpoint_tracking

    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(
        sample_target,
        all_touchpoints,
        role_weighted_rule,
        workflow
    )

    # Should have 1 ledger entry (deal reg partner only)
    assert len(ledger) == 1
    assert ledger[0].partner_id == "P001"
    assert ledger[0].attributed_value == 100000.0  # 100% to deal reg partner


def test_priority_selection_fallback_to_touchpoints(sample_target, touchpoint_tracking, role_weighted_rule):
    """
    Test that touchpoints are used when deal reg doesn't exist.

    Workflow: Priority 1 = Deal Reg, Priority 2 = Touchpoints
    Data: No deal reg, only touchpoints
    Expected: Use touchpoints (fallback)
    """
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Deal Reg Primary",
        description="Test workflow",
        data_sources=[
            DataSourceConfig(
                source_type=DataSource.DEAL_REGISTRATION,
                priority=1,
                enabled=True
            ),
            DataSourceConfig(
                source_type=DataSource.TOUCHPOINT_TRACKING,
                priority=2,
                enabled=True
            )
        ],
        conflict_resolution="priority",
        fallback_strategy="next_priority"
    )

    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(
        sample_target,
        touchpoint_tracking,
        role_weighted_rule,
        workflow
    )

    # Should have 2 ledger entries (both touchpoint partners)
    assert len(ledger) == 2
    partner_ids = {entry.partner_id for entry in ledger}
    assert partner_ids == {"P002", "P003"}


# ============================================================================
# Merge Strategy Tests
# ============================================================================

def test_merge_sources_weighted(sample_target, deal_reg_touchpoint, touchpoint_tracking, role_weighted_rule):
    """
    Test weighted merge: 80% deal reg + 20% touchpoints.

    Expected: All touchpoints combined with weight multipliers applied
    """
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Hybrid 80/20",
        description="Test workflow",
        data_sources=[
            DataSourceConfig(
                source_type=DataSource.DEAL_REGISTRATION,
                priority=1,
                enabled=True,
                config={"attribution_weight": 0.8}
            ),
            DataSourceConfig(
                source_type=DataSource.TOUCHPOINT_TRACKING,
                priority=2,
                enabled=True,
                config={"attribution_weight": 0.2}
            )
        ],
        conflict_resolution="merge",
        fallback_strategy="next_priority"
    )

    all_touchpoints = [deal_reg_touchpoint] + touchpoint_tracking

    # Use activity-weighted model to see weight effect
    activity_rule = AttributionRule(
        id=2,
        name="Activity Weighted",
        model_type=AttributionModel.ACTIVITY_WEIGHTED,
        config={},
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        active=True
    )

    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(
        sample_target,
        all_touchpoints,
        activity_rule,
        workflow
    )

    # Should have 3 ledger entries (all partners)
    assert len(ledger) == 3

    # Deal reg partner should get more (0.8 weight multiplier)
    deal_reg_entry = next(e for e in ledger if e.partner_id == "P001")
    # With weights: P001=0.8, P002=4.0 (5*0.2), P003=0.6 (3*0.2), total=5.4
    # P001 split = 0.8/5.4 = 14.8%
    assert deal_reg_entry.split_percentage > 0.10  # At least 10%


# ============================================================================
# Source Filtering Tests
# ============================================================================

def test_source_filtering_approval_required(sample_target, role_weighted_rule):
    """
    Test that unapproved deal regs are filtered out when approval is required.
    """
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Deal Reg with Approval",
        description="Test workflow",
        data_sources=[
            DataSourceConfig(
                source_type=DataSource.DEAL_REGISTRATION,
                priority=1,
                enabled=True,
                requires_validation=True,
                config={"require_approval": True}
            )
        ],
        conflict_resolution="priority",
        fallback_strategy="manual"
    )

    # Create unapproved deal reg
    unapproved_touchpoint = PartnerTouchpoint(
        id=1,
        partner_id="P001",
        target_id=1,
        touchpoint_type=TouchpointType.DEAL_REGISTRATION,
        role="Referral",
        weight=1.0,
        timestamp=datetime(2024, 12, 1),
        source=DataSource.DEAL_REGISTRATION,
        source_id="DR-123",
        source_confidence=1.0,
        deal_reg_status="pending",
        requires_approval=True,
        approved_by=None  # Not approved
    )

    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(
        sample_target,
        [unapproved_touchpoint],
        role_weighted_rule,
        workflow
    )

    # Should have 0 ledger entries (unapproved touchpoint filtered out)
    assert len(ledger) == 0


def test_source_filtering_deal_reg_expiry(sample_target, role_weighted_rule):
    """
    Test that expired deal regs are filtered out.
    """
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Deal Reg with Expiry",
        description="Test workflow",
        data_sources=[
            DataSourceConfig(
                source_type=DataSource.DEAL_REGISTRATION,
                priority=1,
                enabled=True,
                config={"expiry_days": 90}
            )
        ],
        conflict_resolution="priority",
        fallback_strategy="manual"
    )

    # Create expired deal reg (submitted 120 days ago)
    expired_touchpoint = PartnerTouchpoint(
        id=1,
        partner_id="P001",
        target_id=1,
        touchpoint_type=TouchpointType.DEAL_REGISTRATION,
        role="Referral",
        weight=1.0,
        timestamp=datetime.now() - timedelta(days=120),  # Too old
        source=DataSource.DEAL_REGISTRATION,
        source_id="DR-123",
        source_confidence=1.0,
        deal_reg_status="approved"
    )

    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(
        sample_target,
        [expired_touchpoint],
        role_weighted_rule,
        workflow
    )

    # Should have 0 ledger entries (expired touchpoint filtered out)
    assert len(ledger) == 0


# ============================================================================
# Grouping Tests
# ============================================================================

def test_group_by_source(deal_reg_touchpoint, touchpoint_tracking):
    """Test that touchpoints are correctly grouped by source."""
    all_touchpoints = [deal_reg_touchpoint] + touchpoint_tracking

    engine = AttributionEngine()
    grouped = engine._group_by_source(all_touchpoints)

    assert DataSource.DEAL_REGISTRATION in grouped
    assert len(grouped[DataSource.DEAL_REGISTRATION]) == 1
    assert grouped[DataSource.DEAL_REGISTRATION][0].partner_id == "P001"

    assert DataSource.TOUCHPOINT_TRACKING in grouped
    assert len(grouped[DataSource.TOUCHPOINT_TRACKING]) == 2


# ============================================================================
# Fallback Strategy Tests
# ============================================================================

def test_fallback_equal_split(sample_target, touchpoint_tracking, role_weighted_rule):
    """
    Test equal_split fallback strategy.
    """
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Test Workflow",
        description="Test workflow",
        data_sources=[
            DataSourceConfig(
                source_type=DataSource.DEAL_REGISTRATION,
                priority=1,
                enabled=True
            )
        ],
        conflict_resolution="priority",
        fallback_strategy="equal_split"  # Use all touchpoints with equal weight
    )

    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(
        sample_target,
        touchpoint_tracking,  # No deal reg
        role_weighted_rule,
        workflow
    )

    # Should use fallback (all touchpoints)
    assert len(ledger) == 2


# ============================================================================
# Integration Tests
# ============================================================================

def test_end_to_end_workflow(sample_target, deal_reg_touchpoint, touchpoint_tracking, role_weighted_rule):
    """
    Test complete end-to-end workflow execution.
    """
    # Create workflow
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Deal Reg Primary",
        description="Test workflow",
        data_sources=[
            DataSourceConfig(
                source_type=DataSource.DEAL_REGISTRATION,
                priority=1,
                enabled=True,
                requires_validation=True
            ),
            DataSourceConfig(
                source_type=DataSource.TOUCHPOINT_TRACKING,
                priority=2,
                enabled=True
            )
        ],
        conflict_resolution="priority",
        fallback_strategy="next_priority",
        is_primary=True,
        active=True
    )

    # Approve the deal reg
    deal_reg_touchpoint.approved_by = "admin@test.com"
    deal_reg_touchpoint.requires_approval = True

    all_touchpoints = [deal_reg_touchpoint] + touchpoint_tracking

    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(
        sample_target,
        all_touchpoints,
        role_weighted_rule,
        workflow
    )

    # Verify results
    assert len(ledger) == 1
    assert ledger[0].partner_id == "P001"
    assert ledger[0].target_id == 1
    assert ledger[0].attributed_value == 100000.0
    assert ledger[0].rule_id == 1
    assert ledger[0].audit_trail is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
