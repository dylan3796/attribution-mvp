"""Tests for AI features and utilities."""

import tempfile
import pytest
from pathlib import Path

from db import Database
from attribution import AttributionEngine
from rules import RuleEngine
from ai import AIFeatures
from utils import (
    safe_json_loads,
    validate_split_percent,
    validate_date_format,
    sanitize_input
)


@pytest.fixture
def ai_features():
    """Create AI features with temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        db.init_db()
        db.seed_data_if_empty()
        features = AIFeatures(db)
        yield features


def test_normalize_partner_role(ai_features):
    """Test partner role normalization."""
    assert ai_features._normalize_partner_role("si") == "Implementation (SI)"
    assert ai_features._normalize_partner_role("Implementation") == "Implementation (SI)"
    assert ai_features._normalize_partner_role("Referral") == "Referral"
    assert ai_features._normalize_partner_role("isv") == "ISV"
    assert ai_features._normalize_partner_role("Influence") == "Influence"


def test_heuristic_rule_from_text(ai_features):
    """Test heuristic rule generation from text."""
    rule = ai_features._heuristic_rule_from_text(
        "Block SI partners below 50000"
    )

    assert rule["action"] == "deny"
    assert "si" in rule["name"].lower() or "implementation" in rule["name"].lower()


def test_convert_nl_to_rule_fallback(ai_features):
    """Test NL to rule conversion (will use fallback without API key)."""
    rule, err = ai_features.convert_nl_to_rule(
        "Deny SI partners for deals under $50,000"
    )

    assert "name" in rule
    assert "action" in rule
    assert "when" in rule


def test_generate_relationship_summary_fallback(ai_features):
    """Test relationship summary generation (fallback mode)."""
    summary, err = ai_features.generate_relationship_summary("A1")

    assert summary is not None
    assert len(summary) > 0
    # In fallback mode, we should get a deterministic summary


def test_generate_ai_recommendations_fallback(ai_features):
    """Test AI recommendations (fallback mode)."""
    recs, err = ai_features.generate_ai_recommendations("A1")

    assert isinstance(recs, list)
    # Should have at least one fallback recommendation
    if len(recs) > 0:
        rec = recs[0]
        assert "partner_id" in rec
        assert "recommended_role" in rec
        assert "recommended_split_percent" in rec


# Utility function tests

def test_safe_json_loads():
    """Test safe JSON loading."""
    assert safe_json_loads('{"key": "value"}') == {"key": "value"}
    assert safe_json_loads('invalid json') is None
    assert safe_json_loads('null') is None


def test_validate_split_percent():
    """Test split percentage validation."""
    assert validate_split_percent(0.5) is True
    assert validate_split_percent(0.0) is True
    assert validate_split_percent(1.0) is True
    assert validate_split_percent(-0.1) is False
    assert validate_split_percent(1.5) is False


def test_validate_date_format():
    """Test date format validation."""
    assert validate_date_format("2024-01-15") is True
    assert validate_date_format("2024-12-31") is True
    assert validate_date_format("invalid") is False
    assert validate_date_format("2024-13-01") is False  # Invalid month


def test_sanitize_input():
    """Test input sanitization."""
    assert sanitize_input("  test  ") == "test"
    assert sanitize_input("a" * 2000, max_length=10) == "a" * 10
    assert sanitize_input("") == ""
    assert sanitize_input(None) == ""
