"""Tests for database operations."""

import tempfile
import pytest
from pathlib import Path

from db import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        db.init_db()
        yield db


def test_database_initialization(temp_db):
    """Test that database initializes correctly."""
    # Check that settings table exists and has defaults
    settings = temp_db.read_sql("SELECT * FROM settings;")
    assert not settings.empty
    assert "enforce_split_cap" in settings["setting_key"].values


def test_get_set_setting(temp_db):
    """Test setting get/set operations."""
    temp_db.set_setting("test_key", "test_value")
    value = temp_db.get_setting("test_key", "default")
    assert value == "test_value"

    # Test default value when key doesn't exist
    value = temp_db.get_setting("nonexistent", "default")
    assert value == "default"


def test_get_set_setting_bool(temp_db):
    """Test boolean setting operations."""
    temp_db.set_setting_bool("test_bool", True)
    assert temp_db.get_setting_bool("test_bool", False) is True

    temp_db.set_setting_bool("test_bool", False)
    assert temp_db.get_setting_bool("test_bool", True) is False


def test_seed_data(temp_db):
    """Test data seeding."""
    temp_db.seed_data_if_empty()

    # Check accounts
    accounts = temp_db.read_sql("SELECT * FROM accounts;")
    assert len(accounts) > 0

    # Check partners
    partners = temp_db.read_sql("SELECT * FROM partners;")
    assert len(partners) > 0

    # Check use cases
    use_cases = temp_db.read_sql("SELECT * FROM use_cases;")
    assert len(use_cases) > 0

    # Check revenue events
    revenues = temp_db.read_sql("SELECT * FROM revenue_events;")
    assert len(revenues) > 0


def test_audit_trail(temp_db):
    """Test audit trail logging."""
    temp_db.log_audit_event(
        event_type="test_event",
        account_id="A1",
        partner_id="P1",
        changed_field="split_percent",
        old_value="0.1",
        new_value="0.2",
        source="manual",
        metadata={"test": "data"}
    )

    audit = temp_db.read_sql("SELECT * FROM audit_trail;")
    assert len(audit) == 1
    assert audit.loc[0, "event_type"] == "test_event"
    assert audit.loc[0, "account_id"] == "A1"
