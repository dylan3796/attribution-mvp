"""Data models and type definitions for the Attribution MVP."""

from typing import Optional, Tuple, Dict, List, Any
from dataclasses import dataclass
from datetime import date

# Constants
PARTNER_ROLES = ["Implementation (SI)", "Influence", "Referral", "ISV"]
SCHEMA_VERSION = "1.0"
DB_PATH_DEFAULT = "attribution.db"

# Default settings
DEFAULT_SETTINGS = {
    "enforce_split_cap": "true",
    "si_auto_split_mode": "live_share",
    "si_fixed_percent": "20",
    "default_split_influence": "10",
    "default_split_referral": "15",
    "default_split_isv": "10",
    "allow_manual_split_override": "false",
    "enable_use_case_rules": "true",
    "enable_account_rollup": "true",
    "use_case_tag_source": "hybrid",
    "prompt_rule_conversion": "Convert this rule description into JSON with keys name, action (allow/deny), when (partner_role?, stage?, min_estimated_value?, max_estimated_value?). Only return JSON.",
    "prompt_relationship_summary": "Summarize account relationships with 3 concise bullets: health, risks, next steps.",
    "prompt_ai_recommendations": "Recommend partner attributions. Return JSON list of {partner_id, recommended_role, recommended_split_percent, confidence, reasons}.",
    "schema_version": SCHEMA_VERSION,
}


@dataclass
class AttributionResult:
    """Result from an attribution operation."""
    status: str  # upserted, blocked_split_cap, skipped_manual
    account_id: str
    total_with_new: Optional[float] = None
    message: Optional[str] = None


@dataclass
class RuleContext:
    """Context for rule evaluation."""
    partner_role: Optional[str] = None
    stage: Optional[str] = None
    estimated_value: Optional[float] = None


@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation."""
    allowed: bool
    message: str
    matched_any_rule: bool
    matched_rule_index: Optional[int]
    rule_name: Optional[str]


@dataclass
class ApplySummary:
    """Summary of applying rules."""
    applied: int = 0
    blocked_rule: int = 0
    blocked_cap: int = 0
    skipped_manual: int = 0
    details: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []


@dataclass
class LedgerResult:
    """Result from recomputing attribution ledger."""
    inserted: int = 0
    skipped: int = 0
    blocked: int = 0


@dataclass
class SimulationResult:
    """Result from rule impact simulation."""
    target: str
    lookback_days: int
    checked: int = 0
    allowed: int = 0
    blocked: int = 0
    no_context: int = 0
    revenue_at_risk: float = 0.0
    estimated_value_blocked: float = 0.0
    details: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []
