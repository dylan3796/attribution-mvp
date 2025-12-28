"""
Tests for Universal Attribution Architecture
=============================================

Tests the complete end-to-end flow:
1. Data ingestion (CSV → Targets + Touchpoints)
2. Rule creation (Templates + NL parsing)
3. Attribution calculation (Engine)
4. Ledger generation (Immutable audit trail)
"""

import pytest
import pandas as pd
import io
from datetime import datetime, date, timedelta

# Import new architecture
from models_new import (
    AttributionTarget, PartnerTouchpoint, AttributionRule, LedgerEntry,
    TargetType, TouchpointType, AttributionModel, SplitConstraint,
    validate_rule_config, validate_touchpoint_for_model,
    get_rule_template
)
from attribution_engine import AttributionEngine, select_rule_for_target, get_partner_attribution_summary
from data_ingestion import ingest_csv, generate_csv_template, SchemaDetector
from nl_rule_parser import parse_nl_to_rule
from templates import get_template, list_templates, recommend_template


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_target():
    """Create a sample attribution target (opportunity)"""
    return AttributionTarget(
        id=1,
        type=TargetType.OPPORTUNITY,
        external_id="OPP-001",
        value=100000.0,
        timestamp=datetime(2025, 1, 15),
        metadata={"account_id": "ACC-001", "stage": "Closed Won"}
    )


@pytest.fixture
def sample_touchpoints():
    """Create sample partner touchpoints"""
    return [
        PartnerTouchpoint(
            id=1,
            partner_id="P001",
            target_id=1,
            touchpoint_type=TouchpointType.TAGGED,
            role="Implementation (SI)",
            weight=5.0,
            timestamp=datetime(2025, 1, 1)
        ),
        PartnerTouchpoint(
            id=2,
            partner_id="P002",
            target_id=1,
            touchpoint_type=TouchpointType.TAGGED,
            role="Influence",
            weight=3.0,
            timestamp=datetime(2025, 1, 10)
        )
    ]


@pytest.fixture
def sample_rule_equal_split():
    """Create an equal split rule"""
    return AttributionRule(
        id=1,
        name="Equal Split Test",
        model_type=AttributionModel.EQUAL_SPLIT,
        config={},
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        priority=100,
        active=True
    )


@pytest.fixture
def sample_rule_role_weighted():
    """Create a role-weighted rule"""
    return AttributionRule(
        id=2,
        name="Role-Weighted Test",
        model_type=AttributionModel.ROLE_WEIGHTED,
        config={
            "weights": {
                "Implementation (SI)": 0.6,
                "Influence": 0.4
            }
        },
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        priority=100,
        active=True
    )


# ============================================================================
# Data Model Tests
# ============================================================================

def test_attribution_target_creation(sample_target):
    """Test creating an AttributionTarget"""
    assert sample_target.id == 1
    assert sample_target.type == TargetType.OPPORTUNITY
    assert sample_target.value == 100000.0
    assert sample_target.metadata["account_id"] == "ACC-001"


def test_partner_touchpoint_creation(sample_touchpoints):
    """Test creating PartnerTouchpoints"""
    assert len(sample_touchpoints) == 2
    assert sample_touchpoints[0].partner_id == "P001"
    assert sample_touchpoints[0].role == "Implementation (SI)"
    assert sample_touchpoints[1].weight == 3.0


def test_rule_validation():
    """Test rule config validation"""
    # Valid role-weighted config
    is_valid, error = validate_rule_config(
        AttributionModel.ROLE_WEIGHTED,
        {"weights": {"SI": 0.6, "Influence": 0.4}}
    )
    assert is_valid
    assert error is None

    # Invalid role-weighted config (missing weights)
    is_valid, error = validate_rule_config(
        AttributionModel.ROLE_WEIGHTED,
        {}
    )
    assert not is_valid
    assert "requires 'weights'" in error

    # Invalid time-decay config (missing half_life)
    is_valid, error = validate_rule_config(
        AttributionModel.TIME_DECAY,
        {}
    )
    assert not is_valid


# ============================================================================
# Attribution Engine Tests
# ============================================================================

def test_equal_split_calculation(sample_target, sample_touchpoints, sample_rule_equal_split):
    """Test equal split attribution"""
    engine = AttributionEngine()
    ledger_entries = engine.calculate(sample_target, sample_touchpoints, sample_rule_equal_split)

    assert len(ledger_entries) == 2  # Two partners
    assert ledger_entries[0].split_percentage == 0.5  # 50% each
    assert ledger_entries[1].split_percentage == 0.5
    assert ledger_entries[0].attributed_value == 50000.0  # $50K each
    assert ledger_entries[1].attributed_value == 50000.0


def test_role_weighted_calculation(sample_target, sample_touchpoints, sample_rule_role_weighted):
    """Test role-weighted attribution"""
    engine = AttributionEngine()
    ledger_entries = engine.calculate(sample_target, sample_touchpoints, sample_rule_role_weighted)

    assert len(ledger_entries) == 2

    # Find SI partner (should get 60%)
    si_entry = next(e for e in ledger_entries if e.partner_id == "P001")
    assert si_entry.split_percentage == pytest.approx(0.6)
    assert si_entry.attributed_value == pytest.approx(60000.0)

    # Find Influence partner (should get 40%)
    influence_entry = next(e for e in ledger_entries if e.partner_id == "P002")
    assert influence_entry.split_percentage == pytest.approx(0.4)
    assert influence_entry.attributed_value == pytest.approx(40000.0)


def test_time_decay_calculation(sample_target, sample_touchpoints):
    """Test time-decay attribution"""
    # Create a time-decay rule
    rule = AttributionRule(
        id=3,
        name="Time Decay Test",
        model_type=AttributionModel.TIME_DECAY,
        config={"half_life_days": 7},  # 7-day half-life
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        priority=100,
        active=True
    )

    engine = AttributionEngine()
    ledger_entries = engine.calculate(sample_target, sample_touchpoints, rule)

    assert len(ledger_entries) == 2

    # P002 (Jan 10) should have more credit than P001 (Jan 1) due to recency
    p001_entry = next(e for e in ledger_entries if e.partner_id == "P001")
    p002_entry = next(e for e in ledger_entries if e.partner_id == "P002")

    assert p002_entry.split_percentage > p001_entry.split_percentage
    assert p002_entry.attributed_value > p001_entry.attributed_value


def test_first_touch_calculation(sample_target, sample_touchpoints):
    """Test first-touch attribution"""
    rule = AttributionRule(
        id=4,
        name="First Touch Test",
        model_type=AttributionModel.FIRST_TOUCH,
        config={},
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        priority=100,
        active=True
    )

    engine = AttributionEngine()
    ledger_entries = engine.calculate(sample_target, sample_touchpoints, rule)

    assert len(ledger_entries) == 1  # Only earliest partner
    assert ledger_entries[0].partner_id == "P001"  # Jan 1 is earliest
    assert ledger_entries[0].split_percentage == 1.0
    assert ledger_entries[0].attributed_value == 100000.0


def test_constraint_enforcement():
    """Test split constraint enforcement"""
    engine = AttributionEngine()

    # Test MUST_SUM_TO_100
    splits = {"P001": 0.6, "P002": 0.5}  # Total = 1.1
    normalized = engine._enforce_constraints(splits, SplitConstraint.MUST_SUM_TO_100)
    total = sum(normalized.values())
    assert total == pytest.approx(1.0)

    # Test ALLOW_DOUBLE_COUNTING
    unchanged = engine._enforce_constraints(splits, SplitConstraint.ALLOW_DOUBLE_COUNTING)
    assert unchanged == splits  # No change

    # Test CAP_AT_100
    capped = engine._enforce_constraints(splits, SplitConstraint.CAP_AT_100)
    assert all(v <= 1.0 for v in capped.values())


# ============================================================================
# Data Ingestion Tests
# ============================================================================

def test_csv_ingestion_salesforce():
    """Test ingesting Salesforce-format CSV"""
    csv_data = """opportunity_id,amount,close_date,partner__c,partner_role__c
OPP-001,100000,2025-01-15,Acme Consulting,Implementation (SI)
OPP-002,50000,2025-01-20,Tech Partners,Influence
"""

    result = ingest_csv(csv_data.encode("utf-8"))

    assert result["stats"]["targets_loaded"] == 2
    assert result["stats"]["touchpoints_loaded"] == 2
    assert result["schema"]["target_type"] in ["opportunity", "unknown"]
    assert "opportunity_id" in result["schema"]["mappings"].values()


def test_csv_schema_detection():
    """Test schema auto-detection"""
    detector = SchemaDetector()

    # Test Salesforce schema
    df = pd.DataFrame({
        "opportunity_id": ["OPP-001"],
        "amount": [100000],
        "close_date": ["2025-01-15"],
        "partner__c": ["P001"]
    })

    schema = detector.infer_schema(df)

    assert schema["mappings"]["target_id"] == "opportunity_id"
    assert schema["mappings"]["value"] == "amount"
    assert schema["mappings"]["partner_id"] == "partner__c"
    assert schema["confidence"] > 0.5


def test_csv_template_generation():
    """Test CSV template generation"""
    salesforce_template = generate_csv_template("salesforce")
    assert "opportunity_id" in salesforce_template
    assert "partner__c" in salesforce_template

    hubspot_template = generate_csv_template("hubspot")
    assert "deal_id" in hubspot_template

    minimal_template = generate_csv_template("minimal")
    assert "target_id" in minimal_template


# ============================================================================
# Natural Language Parser Tests
# ============================================================================

def test_nl_parser_equal_split():
    """Test parsing 'equal split' natural language"""
    success, config, error = parse_nl_to_rule("Split evenly among all partners")

    assert success
    assert config["model_type"] == "equal_split"
    assert error is None


def test_nl_parser_first_touch():
    """Test parsing 'first touch' natural language"""
    success, config, error = parse_nl_to_rule("First partner to touch the deal gets 100%")

    assert success
    assert config["model_type"] == "first_touch"


def test_nl_parser_time_decay():
    """Test parsing 'time decay' natural language"""
    success, config, error = parse_nl_to_rule("More recent partner touches get more credit with 30 day half-life")

    assert success
    assert config["model_type"] == "time_decay"
    assert config["config"]["half_life_days"] == 30


def test_nl_parser_role_weighted():
    """Test parsing role-weighted natural language"""
    success, config, error = parse_nl_to_rule("SI 60%, Influence 40%")

    assert success
    assert config["model_type"] == "role_weighted"
    assert "weights" in config["config"]


# ============================================================================
# Template Tests
# ============================================================================

def test_template_retrieval():
    """Test getting templates by ID"""
    template = get_template("equal_split_all")
    assert template is not None
    assert template["model_type"] == "equal_split"

    template = get_template("saas_b2b")
    assert template is not None
    assert template["model_type"] == "role_weighted"


def test_template_listing():
    """Test listing templates by category"""
    all_templates = list_templates()
    assert len(all_templates) > 0

    industry_templates = list_templates("industry")
    assert len(industry_templates) > 0

    deal_size_templates = list_templates("deal_size")
    assert len(deal_size_templates) > 0


def test_template_recommendation():
    """Test template recommendation"""
    # Growth-stage SaaS company
    rec = recommend_template(company_size="growth", industry="saas", partner_program_maturity="growth")
    assert rec == "saas_b2b"

    # Early-stage company
    rec = recommend_template(partner_program_maturity="early")
    assert rec == "early_stage"

    # Cloud infrastructure
    rec = recommend_template(industry="cloud")
    assert rec == "cloud_infrastructure"


# ============================================================================
# Rule Selection Tests
# ============================================================================

def test_rule_selection_single_match(sample_target):
    """Test selecting a rule when one matches"""
    rules = [
        AttributionRule(
            id=1,
            name="Test Rule",
            model_type=AttributionModel.EQUAL_SPLIT,
            config={},
            split_constraint=SplitConstraint.MUST_SUM_TO_100,
            priority=100,
            active=True
        )
    ]

    selected = select_rule_for_target(sample_target, rules)
    assert selected is not None
    assert selected.id == 1


def test_rule_selection_priority(sample_target):
    """Test that highest priority rule is selected"""
    rules = [
        AttributionRule(
            id=1,
            name="Low Priority",
            model_type=AttributionModel.EQUAL_SPLIT,
            config={},
            priority=200,
            active=True
        ),
        AttributionRule(
            id=2,
            name="High Priority",
            model_type=AttributionModel.FIRST_TOUCH,
            config={},
            priority=50,  # Lower number = higher priority
            active=True
        )
    ]

    selected = select_rule_for_target(sample_target, rules)
    assert selected.id == 2  # High priority rule


def test_rule_selection_with_filters():
    """Test rule selection with applies_to filters"""
    target_small = AttributionTarget(
        id=1,
        type=TargetType.OPPORTUNITY,
        external_id="SMALL-001",
        value=10000.0,
        timestamp=datetime(2025, 1, 15),
        metadata={}
    )

    target_large = AttributionTarget(
        id=2,
        type=TargetType.OPPORTUNITY,
        external_id="LARGE-001",
        value=500000.0,
        timestamp=datetime(2025, 1, 15),
        metadata={}
    )

    rules = [
        AttributionRule(
            id=1,
            name="Enterprise Only",
            model_type=AttributionModel.ROLE_WEIGHTED,
            config={"weights": {"SI": 0.7, "Influence": 0.3}},
            applies_to={"min_value": 100000},  # Only for deals >$100K
            priority=100,
            active=True
        ),
        AttributionRule(
            id=2,
            name="Default",
            model_type=AttributionModel.EQUAL_SPLIT,
            config={},
            priority=200,
            active=True
        )
    ]

    # Small deal should use default rule
    selected = select_rule_for_target(target_small, rules)
    assert selected.id == 2

    # Large deal should use enterprise rule
    selected = select_rule_for_target(target_large, rules)
    assert selected.id == 1


# ============================================================================
# End-to-End Integration Test
# ============================================================================

def test_end_to_end_attribution_flow():
    """
    Complete end-to-end test:
    1. Ingest CSV data
    2. Create attribution rule
    3. Calculate attribution
    4. Verify ledger entries
    """
    # Step 1: Ingest data
    csv_data = """target_id,value,timestamp,partner_id,role
T001,100000,2025-01-15,P001,Implementation (SI)
T001,100000,2025-01-15,P002,Influence
T002,50000,2025-01-20,P002,Influence
"""

    result = ingest_csv(csv_data.encode("utf-8"))

    assert result["stats"]["targets_loaded"] == 2
    assert result["stats"]["touchpoints_loaded"] == 3

    targets = result["targets"]
    touchpoints = result["touchpoints"]

    # Step 2: Create rule
    rule = AttributionRule(
        id=1,
        name="Role-Weighted",
        model_type=AttributionModel.ROLE_WEIGHTED,
        config={"weights": {"Implementation (SI)": 0.6, "Influence": 0.4}},
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        priority=100,
        active=True
    )

    # Step 3: Calculate attribution
    engine = AttributionEngine()
    all_ledger_entries = []

    for target in targets:
        target_touchpoints = [tp for tp in touchpoints if tp.target_id == target.id]
        if target_touchpoints:
            entries = engine.calculate(target, target_touchpoints, rule)
            all_ledger_entries.extend(entries)

    # Step 4: Verify results
    assert len(all_ledger_entries) > 0

    # Verify total attributed equals target values
    total_attributed = sum(e.attributed_value for e in all_ledger_entries)
    total_target_value = sum(t.value for t in targets)
    assert total_attributed == pytest.approx(total_target_value)

    # Verify audit trails exist
    for entry in all_ledger_entries:
        assert "rule_name" in entry.audit_trail
        assert "calculation_steps" in entry.audit_trail


# ============================================================================
# Performance Tests
# ============================================================================

def test_attribution_performance_100_targets():
    """Test attribution performance with 100 targets"""
    import time

    # Create 100 targets
    targets = [
        AttributionTarget(
            id=i,
            type=TargetType.OPPORTUNITY,
            external_id=f"OPP-{i:03d}",
            value=100000.0,
            timestamp=datetime(2025, 1, 15),
            metadata={}
        )
        for i in range(100)
    ]

    # Create 200 touchpoints (2 per target)
    touchpoints = []
    for target in targets:
        touchpoints.append(PartnerTouchpoint(
            id=target.id * 2,
            partner_id="P001",
            target_id=target.id,
            touchpoint_type=TouchpointType.TAGGED,
            role="Implementation (SI)",
            timestamp=datetime(2025, 1, 1)
        ))
        touchpoints.append(PartnerTouchpoint(
            id=target.id * 2 + 1,
            partner_id="P002",
            target_id=target.id,
            touchpoint_type=TouchpointType.TAGGED,
            role="Influence",
            timestamp=datetime(2025, 1, 10)
        ))

    # Create rule
    rule = AttributionRule(
        id=1,
        name="Equal Split",
        model_type=AttributionModel.EQUAL_SPLIT,
        config={},
        split_constraint=SplitConstraint.MUST_SUM_TO_100,
        priority=100,
        active=True
    )

    # Time the calculation
    engine = AttributionEngine()
    start_time = time.time()

    all_entries = []
    for target in targets:
        target_touchpoints = [tp for tp in touchpoints if tp.target_id == target.id]
        entries = engine.calculate(target, target_touchpoints, rule)
        all_entries.extend(entries)

    elapsed = time.time() - start_time

    assert len(all_entries) == 200  # 2 partners x 100 targets
    assert elapsed < 1.0  # Should complete in under 1 second
    print(f"Attribution for 100 targets completed in {elapsed:.3f}s")
