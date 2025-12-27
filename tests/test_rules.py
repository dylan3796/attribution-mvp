"""Tests for rule engine."""

import tempfile
import pytest
from pathlib import Path

from db import Database
from rules import RuleEngine


@pytest.fixture
def rule_engine():
    """Create a rule engine with temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        db.init_db()
        engine = RuleEngine(db)
        yield engine


def test_rule_matching_role(rule_engine):
    """Test rule matching based on partner role."""
    rules = [
        {
            "name": "Block SI",
            "action": "deny",
            "when": {"partner_role": "Implementation (SI)"}
        }
    ]
    rule_engine.save_rules("test_rules", rules)

    # Test matching role
    result = rule_engine.evaluate_rules(
        {"partner_role": "Implementation (SI)"},
        "test_rules"
    )
    assert result.allowed is False
    assert "Block SI" in result.message

    # Test non-matching role
    result = rule_engine.evaluate_rules(
        {"partner_role": "Influence"},
        "test_rules"
    )
    assert result.allowed is False  # No matching rule, blocked by default


def test_rule_matching_value_range(rule_engine):
    """Test rule matching based on estimated value ranges."""
    rules = [
        {
            "name": "Block small deals",
            "action": "deny",
            "when": {"max_estimated_value": 10000}
        },
        {
            "name": "Allow all",
            "action": "allow",
            "when": {}
        }
    ]
    rule_engine.save_rules("test_rules", rules)

    # Test small value (should be blocked)
    result = rule_engine.evaluate_rules(
        {"estimated_value": 5000},
        "test_rules"
    )
    assert result.allowed is False

    # Test large value (should be allowed)
    result = rule_engine.evaluate_rules(
        {"estimated_value": 50000},
        "test_rules"
    )
    assert result.allowed is True


def test_rule_matching_stage(rule_engine):
    """Test rule matching based on stage."""
    rules = [
        {
            "name": "Allow Discovery only",
            "action": "allow",
            "when": {"stage": "Discovery"}
        }
    ]
    rule_engine.save_rules("test_rules", rules)

    result = rule_engine.evaluate_rules(
        {"stage": "Discovery"},
        "test_rules"
    )
    assert result.allowed is True

    result = rule_engine.evaluate_rules(
        {"stage": "Live"},
        "test_rules"
    )
    assert result.allowed is False


def test_validate_rule_object(rule_engine):
    """Test rule validation."""
    valid_rule = {
        "name": "Test",
        "action": "allow",
        "when": {}
    }
    assert rule_engine.validate_rule_obj(valid_rule) is True

    # Missing action
    invalid_rule = {
        "name": "Test",
        "when": {}
    }
    assert rule_engine.validate_rule_obj(invalid_rule) is False

    # Invalid action
    invalid_rule = {
        "name": "Test",
        "action": "invalid",
        "when": {}
    }
    assert rule_engine.validate_rule_obj(invalid_rule) is False


def test_rule_version_hash(rule_engine):
    """Test that rule version changes when rules change."""
    rules1 = [{"name": "Rule 1", "action": "allow", "when": {}}]
    rule_engine.save_rules("test_rules", rules1)
    version1 = rule_engine.get_rule_version("test_rules")

    rules2 = [{"name": "Rule 2", "action": "deny", "when": {}}]
    rule_engine.save_rules("test_rules", rules2)
    version2 = rule_engine.get_rule_version("test_rules")

    assert version1 != version2
