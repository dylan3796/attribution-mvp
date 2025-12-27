"""Tests for attribution engine."""

import tempfile
import pytest
from pathlib import Path
from datetime import date, timedelta

from db import Database
from rules import RuleEngine
from attribution import AttributionEngine


@pytest.fixture
def attribution_engine():
    """Create an attribution engine with temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        db.init_db()
        db.seed_data_if_empty()
        rule_engine = RuleEngine(db)
        engine = AttributionEngine(db, rule_engine)
        yield engine


def test_split_cap_enforcement(attribution_engine):
    """Test split cap enforcement."""
    # Add a partner with 60% split
    attribution_engine.db.run_sql(
        "INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source) "
        "VALUES (?, ?, ?, date('now'), date('now'), 'auto');",
        ("A1", "P1", 0.6)
    )

    # Try to add another partner with 50% (should exceed cap)
    exceeds, total = attribution_engine.will_exceed_split_cap("A1", "P2", 0.5)
    assert exceeds == True  # Use == instead of is for numpy bool compatibility
    assert total == 1.1


def test_compute_si_auto_split_live_share(attribution_engine):
    """Test SI auto split calculation in live_share mode."""
    split, reason = attribution_engine.compute_si_auto_split(
        use_case_value=100.0,
        account_live_total=200.0,
        account_all_total=300.0,
        mode="live_share"
    )
    assert split == 0.5
    assert "use case" in reason.lower()


def test_compute_si_auto_split_fixed_percent(attribution_engine):
    """Test SI auto split calculation in fixed_percent mode."""
    attribution_engine.db.set_setting("si_fixed_percent", "30")
    split, reason = attribution_engine.compute_si_auto_split(
        use_case_value=100.0,
        account_live_total=0.0,
        account_all_total=0.0,
        mode="fixed_percent"
    )
    assert split == 0.3
    assert "fixed" in reason.lower()


def test_upsert_account_partner(attribution_engine):
    """Test upserting account partners."""
    # Create a use case first
    use_case_id = attribution_engine.create_use_case(
        account_id="A1",
        use_case_name="Test Use Case",
        stage="Discovery",
        estimated_value=50000.0,
        target_close_date=(date.today() + timedelta(days=30)).isoformat()
    )

    # Upsert account partner
    result = attribution_engine.upsert_account_partner_from_use_case_partner(
        use_case_id=use_case_id,
        partner_id="P1",
        partner_role="Influence",
        split_percent=0.15
    )

    assert result.status == "upserted"
    assert result.account_id == "A1"

    # Verify it was inserted
    ap = attribution_engine.db.read_sql(
        "SELECT * FROM account_partners WHERE account_id = ? AND partner_id = ?;",
        ("A1", "P1")
    )
    assert len(ap) == 1
    assert float(ap.loc[0, "split_percent"]) == 0.15


def test_manual_split_override(attribution_engine):
    """Test that manual splits are not overridden."""
    # Set manual split
    attribution_engine.upsert_manual_account_partner("A1", "P1", 0.25)

    # Verify source is manual
    ap = attribution_engine.db.read_sql(
        "SELECT source FROM account_partners WHERE account_id = ? AND partner_id = ?;",
        ("A1", "P1")
    )
    assert ap.loc[0, "source"] == "manual"

    # Try to auto-update (should be skipped)
    use_case_id = attribution_engine.create_use_case(
        account_id="A1",
        use_case_name="Test",
        stage="Live",
        estimated_value=10000.0,
        target_close_date=date.today().isoformat()
    )

    result = attribution_engine.upsert_account_partner_from_use_case_partner(
        use_case_id=use_case_id,
        partner_id="P1",
        partner_role="Influence",
        split_percent=0.10
    )

    assert result.status == "skipped_manual"

    # Verify split didn't change
    ap = attribution_engine.db.read_sql(
        "SELECT split_percent FROM account_partners WHERE account_id = ? AND partner_id = ?;",
        ("A1", "P1")
    )
    assert float(ap.loc[0, "split_percent"]) == 0.25


def test_recompute_ledger(attribution_engine):
    """Test attribution ledger recomputation."""
    # Add account partner
    attribution_engine.db.run_sql(
        "INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source) "
        "VALUES (?, ?, ?, date('now'), date('now'), 'auto');",
        ("A1", "P1", 0.5)
    )

    # Recompute ledger
    result = attribution_engine.recompute_attribution_ledger(days=30)

    assert result.inserted > 0

    # Verify attribution events were created
    events = attribution_engine.db.read_sql(
        "SELECT * FROM attribution_events WHERE account_id = ?;",
        ("A1",)
    )
    assert len(events) > 0


def test_create_use_case(attribution_engine):
    """Test use case creation."""
    use_case_id = attribution_engine.create_use_case(
        account_id="A1",
        use_case_name="New Use Case",
        stage="Evaluation",
        estimated_value=75000.0,
        target_close_date=(date.today() + timedelta(days=60)).isoformat(),
        tag_source="app"
    )

    assert use_case_id.startswith("UC-")

    # Verify it was created
    uc = attribution_engine.db.read_sql(
        "SELECT * FROM use_cases WHERE use_case_id = ?;",
        (use_case_id,)
    )
    assert len(uc) == 1
    assert uc.loc[0, "use_case_name"] == "New Use Case"
    assert uc.loc[0, "stage"] == "Evaluation"
