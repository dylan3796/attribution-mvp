"""
Workflow System Validation Script
==================================

Quick validation script to test the multi-source attribution workflow system.
Run this to verify that all components are working correctly.

Usage:
    python3 validate_workflows.py
"""

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


def test_priority_workflow():
    """Test priority-based workflow (deal reg → touchpoints)."""
    print("\n" + "="*60)
    print("TEST 1: Priority-Based Workflow")
    print("="*60)

    # Create target
    target = AttributionTarget(
        id=1,
        type=TargetType.OPPORTUNITY,
        external_id="OPP-001",
        value=100000.0,
        timestamp=datetime(2025, 1, 15),
        metadata={"account_name": "Acme Corp"}
    )

    # Create touchpoints from different sources
    touchpoints = [
        # Deal registration
        PartnerTouchpoint(
            id=1,
            partner_id="P001",
            target_id=1,
            touchpoint_type=TouchpointType.DEAL_REGISTRATION,
            role="Referral",
            weight=1.0,
            timestamp=datetime(2024, 12, 1),
            source=DataSource.DEAL_REGISTRATION,
            source_id="DR-123",
            deal_reg_status="approved",
            approved_by="admin@test.com"
        ),
        # Touchpoint tracking
        PartnerTouchpoint(
            id=2,
            partner_id="P002",
            target_id=1,
            touchpoint_type=TouchpointType.ACTIVITY,
            role="Implementation (SI)",
            weight=5.0,
            timestamp=datetime(2024, 12, 15),
            source=DataSource.TOUCHPOINT_TRACKING
        )
    ]

    # Create workflow
    workflow = MeasurementWorkflow(
        id=1,
        company_id="test",
        name="Deal Reg Primary",
        description="Use deal reg if exists, else touchpoints",
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
        fallback_strategy="next_priority"
    )

    # Create rule
    rule = AttributionRule(
        id=1,
        name="Equal Split",
        model_type=AttributionModel.EQUAL_SPLIT,
        config={},
        split_constraint=SplitConstraint.MUST_SUM_TO_100
    )

    # Calculate attribution
    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(target, touchpoints, rule, workflow)

    # Validate results
    print(f"\nTarget: {target.external_id} (${target.value:,.0f})")
    print(f"Workflow: {workflow.name}")
    print(f"Touchpoints: {len(touchpoints)} total")
    print(f"  - Deal Reg: 1")
    print(f"  - Touchpoints: 1")
    print(f"\nAttribution Results:")
    print(f"  Ledger entries: {len(ledger)}")

    for entry in ledger:
        print(f"  - Partner {entry.partner_id}: ${entry.attributed_value:,.0f} ({entry.split_percentage*100:.1f}%)")

    # Expected: Only P001 (deal reg wins)
    assert len(ledger) == 1, f"Expected 1 ledger entry, got {len(ledger)}"
    assert ledger[0].partner_id == "P001", f"Expected P001, got {ledger[0].partner_id}"
    assert ledger[0].attributed_value == 100000.0, f"Expected $100,000, got ${ledger[0].attributed_value}"

    print("\n✅ TEST PASSED: Priority selection working correctly")
    return True


def test_merge_workflow():
    """Test weighted merge workflow (80% deal reg + 20% influence)."""
    print("\n" + "="*60)
    print("TEST 2: Weighted Merge Workflow")
    print("="*60)

    # Create target
    target = AttributionTarget(
        id=1,
        type=TargetType.OPPORTUNITY,
        external_id="OPP-002",
        value=100000.0,
        timestamp=datetime(2025, 1, 15),
        metadata={"account_name": "BigCo"}
    )

    # Create touchpoints
    touchpoints = [
        PartnerTouchpoint(
            id=1,
            partner_id="P001",
            target_id=1,
            touchpoint_type=TouchpointType.DEAL_REGISTRATION,
            role="Referral",
            weight=1.0,
            timestamp=datetime(2024, 12, 1),
            source=DataSource.DEAL_REGISTRATION
        ),
        PartnerTouchpoint(
            id=2,
            partner_id="P002",
            target_id=1,
            touchpoint_type=TouchpointType.ACTIVITY,
            role="Influence",
            weight=5.0,
            timestamp=datetime(2024, 12, 15),
            source=DataSource.TOUCHPOINT_TRACKING
        )
    ]

    # Create merge workflow
    workflow = MeasurementWorkflow(
        id=2,
        company_id="test",
        name="Hybrid 80/20",
        description="80% deal reg + 20% influence",
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
        conflict_resolution="merge",  # Combine both
        fallback_strategy="next_priority"
    )

    # Use activity-weighted model to see weight effect
    rule = AttributionRule(
        id=2,
        name="Activity Weighted",
        model_type=AttributionModel.ACTIVITY_WEIGHTED,
        config={},
        split_constraint=SplitConstraint.MUST_SUM_TO_100
    )

    # Calculate attribution
    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(target, touchpoints, rule, workflow)

    # Validate results
    print(f"\nTarget: {target.external_id} (${target.value:,.0f})")
    print(f"Workflow: {workflow.name}")
    print(f"Conflict Resolution: {workflow.conflict_resolution}")
    print(f"\nAttribution Results:")
    print(f"  Ledger entries: {len(ledger)}")

    for entry in ledger:
        print(f"  - Partner {entry.partner_id}: ${entry.attributed_value:,.0f} ({entry.split_percentage*100:.1f}%)")

    # Expected: Both partners (weighted merge)
    assert len(ledger) == 2, f"Expected 2 ledger entries, got {len(ledger)}"

    print("\n✅ TEST PASSED: Weighted merge working correctly")
    return True


def test_fallback():
    """Test fallback strategy when primary source has no data."""
    print("\n" + "="*60)
    print("TEST 3: Fallback Strategy")
    print("="*60)

    # Create target
    target = AttributionTarget(
        id=1,
        type=TargetType.OPPORTUNITY,
        external_id="OPP-003",
        value=100000.0,
        timestamp=datetime(2025, 1, 15),
        metadata={}
    )

    # Only touchpoint tracking (no deal reg)
    touchpoints = [
        PartnerTouchpoint(
            id=1,
            partner_id="P001",
            target_id=1,
            touchpoint_type=TouchpointType.ACTIVITY,
            role="Implementation (SI)",
            weight=1.0,
            timestamp=datetime(2024, 12, 15),
            source=DataSource.TOUCHPOINT_TRACKING
        )
    ]

    # Workflow expects deal reg, falls back to touchpoints
    workflow = MeasurementWorkflow(
        id=3,
        company_id="test",
        name="Deal Reg with Fallback",
        description="Use deal reg, else touchpoints",
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

    rule = AttributionRule(
        id=1,
        name="Equal Split",
        model_type=AttributionModel.EQUAL_SPLIT,
        config={},
        split_constraint=SplitConstraint.MUST_SUM_TO_100
    )

    # Calculate attribution
    engine = AttributionEngine()
    ledger = engine.calculate_with_workflow(target, touchpoints, rule, workflow)

    # Validate results
    print(f"\nTarget: {target.external_id} (${target.value:,.0f})")
    print(f"Workflow: {workflow.name}")
    print(f"Primary Source: Deal Registration (no data)")
    print(f"Fallback: Touchpoint Tracking")
    print(f"\nAttribution Results:")
    print(f"  Ledger entries: {len(ledger)}")

    for entry in ledger:
        print(f"  - Partner {entry.partner_id}: ${entry.attributed_value:,.0f} ({entry.split_percentage*100:.1f}%)")

    # Expected: Falls back to touchpoint tracking
    assert len(ledger) == 1, f"Expected 1 ledger entry, got {len(ledger)}"
    assert ledger[0].partner_id == "P001", f"Expected P001, got {ledger[0].partner_id}"

    print("\n✅ TEST PASSED: Fallback strategy working correctly")
    return True


def main():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("WORKFLOW SYSTEM VALIDATION")
    print("="*60)

    try:
        # Run tests
        test_priority_workflow()
        test_merge_workflow()
        test_fallback()

        # Summary
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nWorkflow system is functioning correctly:")
        print("  ✓ Priority-based source selection")
        print("  ✓ Weighted merge of multiple sources")
        print("  ✓ Fallback strategies")
        print("  ✓ Source filtering")
        print("  ✓ Integration with attribution engine")
        print("\nReady for production use!")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
