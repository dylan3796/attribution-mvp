"""
Data models and type definitions for the Attribution MVP.

This module defines:
1. Simple dataclasses for rule evaluation and attribution results
2. Universal attribution models (targets, touchpoints, rules, ledger)
3. Enums for type safety
4. Validation functions
5. Rule templates
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Tuple, Dict, List, Any
from enum import Enum
import json


# ============================================================================
# Constants
# ============================================================================

PARTNER_ROLES = ["Implementation (SI)", "Influence", "Referral", "ISV"]
SCHEMA_VERSION = "2.0"
DB_PATH_DEFAULT = "attribution.db"

# Default partner roles (extensible by users)
DEFAULT_PARTNER_ROLES = [
    "Implementation (SI)",
    "Influence",
    "Referral",
    "ISV",
    "Reseller",
    "Technology Partner",
    "Consulting",
    "Sourcing"
]

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


# ============================================================================
# Enums
# ============================================================================

class TargetType(str, Enum):
    """What is being attributed"""
    OPPORTUNITY = "opportunity"          # Salesforce/HubSpot deal
    CONSUMPTION_EVENT = "consumption"    # Usage-based (Databricks, Snowflake)
    ACCOUNT = "account"                  # Account-level attribution
    CUSTOM = "custom"                    # User-defined target type


class TouchpointType(str, Enum):
    """How partner involvement is evidenced"""
    TAGGED = "tagged"                    # Partner tagged in CRM
    CONTACT_ROLE = "contact_role"        # OpportunityContactRole
    ACTIVITY = "activity"                # Meetings, emails, calls
    REFERRAL = "referral"                # Explicit referral
    MANUAL_OVERRIDE = "manual_override"  # AE manually assigned
    CONSUMPTION_TAG = "consumption_tag"  # Usage data tagged with partner
    DEAL_REGISTRATION = "deal_registration"
    CRM_PARTNER_FIELD = "crm_partner_field"
    MARKETPLACE_TRANSACTION = "marketplace"
    PARTNER_SELF_REPORTED = "partner_self_reported"
    INTEGRATION_TAG = "integration_tag"
    SOURCED_BY = "sourced_by"


class DataSource(str, Enum):
    """Available measurement data sources"""
    DEAL_REGISTRATION = "deal_registration"
    CRM_OPPORTUNITY_FIELD = "crm_opportunity_field"
    TOUCHPOINT_TRACKING = "touchpoint_tracking"
    MARKETPLACE_TRANSACTIONS = "marketplace_transactions"
    PARTNER_PORTAL_REPORTING = "partner_portal_reporting"
    ACTIVITY_TRACKING = "activity_tracking"
    MANUAL_OVERRIDE = "manual_override"


class AttributionModel(str, Enum):
    """Attribution calculation methodologies"""
    EQUAL_SPLIT = "equal_split"
    ROLE_WEIGHTED = "role_weighted"
    ACTIVITY_WEIGHTED = "activity_weighted"
    TIME_DECAY = "time_decay"
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    U_SHAPED = "u_shaped"
    W_SHAPED = "w_shaped"
    CUSTOM = "custom"


class SplitConstraint(str, Enum):
    """How to enforce split percentages"""
    MUST_SUM_TO_100 = "must_sum_to_100"
    ALLOW_DOUBLE_COUNTING = "allow_double_counting"
    CAP_AT_100 = "cap_at_100"
    NO_CONSTRAINT = "no_constraint"


class PeriodType(str, Enum):
    """Type of attribution period"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class PeriodStatus(str, Enum):
    """Status of an attribution period"""
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


# ============================================================================
# Simple Dataclasses (Original System)
# ============================================================================

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


# ============================================================================
# Universal Attribution Dataclasses
# ============================================================================

@dataclass
class AttributionTarget:
    """
    What gets credit - an opportunity, consumption event, or account.
    """
    id: int
    type: TargetType
    external_id: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, TargetType) else self.type,
            "external_id": self.external_id,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": json.dumps(self.metadata) if isinstance(self.metadata, dict) else self.metadata,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class PartnerTouchpoint:
    """Evidence of partner involvement with a target."""
    id: int
    partner_id: str
    target_id: int
    touchpoint_type: TouchpointType
    role: str
    weight: float = 1.0
    timestamp: Optional[datetime] = None
    source: DataSource = DataSource.TOUCHPOINT_TRACKING
    source_id: Optional[str] = None
    source_confidence: float = 1.0
    deal_reg_status: Optional[str] = None
    deal_reg_submitted_date: Optional[datetime] = None
    deal_reg_approved_date: Optional[datetime] = None
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "target_id": self.target_id,
            "touchpoint_type": self.touchpoint_type.value if isinstance(self.touchpoint_type, TouchpointType) else self.touchpoint_type,
            "role": self.role,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source.value if isinstance(self.source, DataSource) else self.source,
            "source_id": self.source_id,
            "source_confidence": self.source_confidence,
            "deal_reg_status": self.deal_reg_status,
            "deal_reg_submitted_date": self.deal_reg_submitted_date.isoformat() if self.deal_reg_submitted_date else None,
            "deal_reg_approved_date": self.deal_reg_approved_date.isoformat() if self.deal_reg_approved_date else None,
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approval_timestamp": self.approval_timestamp.isoformat() if self.approval_timestamp else None,
            "metadata": json.dumps(self.metadata) if isinstance(self.metadata, dict) else self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class DataSourceConfig:
    """Configuration for a data source type within a measurement workflow."""
    source_type: DataSource
    enabled: bool = True
    priority: int = 100
    auto_create_touchpoints: bool = True
    requires_validation: bool = False
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type.value if isinstance(self.source_type, DataSource) else self.source_type,
            "enabled": self.enabled,
            "priority": self.priority,
            "auto_create_touchpoints": self.auto_create_touchpoints,
            "requires_validation": self.requires_validation,
            "config": json.dumps(self.config) if isinstance(self.config, dict) else self.config
        }


@dataclass
class MeasurementWorkflow:
    """Defines HOW a company measures partner contribution."""
    id: int
    company_id: str
    name: str
    description: str
    data_sources: List[DataSourceConfig] = field(default_factory=list)
    conflict_resolution: str = "priority"
    fallback_strategy: str = "next_priority"
    applies_to: Dict[str, Any] = field(default_factory=dict)
    is_primary: bool = False
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "description": self.description,
            "data_sources": json.dumps([ds.to_dict() for ds in self.data_sources]),
            "conflict_resolution": self.conflict_resolution,
            "fallback_strategy": self.fallback_strategy,
            "applies_to": json.dumps(self.applies_to) if isinstance(self.applies_to, dict) else self.applies_to,
            "is_primary": self.is_primary,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


@dataclass
class AttributionRule:
    """Configuration-driven rule for calculating attribution splits."""
    id: int
    name: str
    model_type: AttributionModel
    config: Dict[str, Any]
    applies_to: Dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    split_constraint: SplitConstraint = SplitConstraint.MUST_SUM_TO_100
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_type": self.model_type.value if isinstance(self.model_type, AttributionModel) else self.model_type,
            "config": json.dumps(self.config) if isinstance(self.config, dict) else self.config,
            "applies_to": json.dumps(self.applies_to) if isinstance(self.applies_to, dict) else self.applies_to,
            "priority": self.priority,
            "split_constraint": self.split_constraint.value if isinstance(self.split_constraint, SplitConstraint) else self.split_constraint,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }

    def matches_target(self, target: AttributionTarget) -> bool:
        """Check if this rule applies to a given target"""
        if not self.applies_to:
            return True

        if "target_type" in self.applies_to:
            target_type_val = target.type.value if isinstance(target.type, TargetType) else target.type
            if target_type_val != self.applies_to["target_type"]:
                return False

        if "metadata" in self.applies_to:
            for key, expected_value in self.applies_to["metadata"].items():
                if key not in target.metadata:
                    return False
                if target.metadata[key] != expected_value:
                    return False

        if "min_value" in self.applies_to:
            if target.value < self.applies_to["min_value"]:
                return False
        if "max_value" in self.applies_to:
            if target.value > self.applies_to["max_value"]:
                return False

        return True


@dataclass
class LedgerEntry:
    """Immutable attribution result - output of the calculation engine."""
    id: int
    target_id: int
    partner_id: str
    attributed_value: float
    split_percentage: float
    rule_id: int
    calculation_timestamp: datetime
    role: str = ""
    attribution_percentage: float = 0.0
    override_by: Optional[str] = None
    override_reason: Optional[str] = None
    audit_trail: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_id": self.target_id,
            "partner_id": self.partner_id,
            "attributed_value": self.attributed_value,
            "split_percentage": self.split_percentage,
            "rule_id": self.rule_id,
            "calculation_timestamp": self.calculation_timestamp.isoformat() if self.calculation_timestamp else None,
            "role": self.role,
            "attribution_percentage": self.attribution_percentage,
            "override_by": self.override_by,
            "audit_trail": json.dumps(self.audit_trail) if isinstance(self.audit_trail, dict) else self.audit_trail,
            "metadata": json.dumps(self.metadata) if isinstance(self.metadata, dict) else self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def explain(self) -> str:
        """Human-readable explanation of this ledger entry"""
        rule_name = self.audit_trail.get("rule_name", "Unknown") if isinstance(self.audit_trail, dict) else "Unknown"
        model_type = self.audit_trail.get("model_type", "Unknown") if isinstance(self.audit_trail, dict) else "Unknown"

        explanation = (
            f"Partner {self.partner_id} received ${self.attributed_value:,.2f} "
            f"({self.split_percentage:.1%} split) from Target {self.target_id} "
            f"using '{rule_name}' rule ({model_type} model)."
        )

        if isinstance(self.audit_trail, dict) and "calculation_steps" in self.audit_trail:
            explanation += f"\n\nCalculation steps:\n{self.audit_trail['calculation_steps']}"

        return explanation


@dataclass
class AttributionPeriod:
    """Represents a time period for attribution calculations."""
    id: int
    organization_id: str
    name: str
    period_type: PeriodType
    start_date: datetime
    end_date: datetime
    status: PeriodStatus = PeriodStatus.OPEN
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    total_revenue: float = 0.0
    total_deals: int = 0
    total_partners: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def is_open(self) -> bool:
        return self.status == PeriodStatus.OPEN

    def is_closed(self) -> bool:
        return self.status in [PeriodStatus.CLOSED, PeriodStatus.LOCKED]

    def is_locked(self) -> bool:
        return self.status == PeriodStatus.LOCKED

    def can_recalculate(self) -> bool:
        return self.status != PeriodStatus.LOCKED

    def contains_date(self, check_date: datetime) -> bool:
        return self.start_date <= check_date <= self.end_date


# ============================================================================
# Rule Templates
# ============================================================================

RULE_TEMPLATES = {
    "equal_split_all": {
        "name": "Equal Split - All Partners",
        "model_type": AttributionModel.EQUAL_SPLIT,
        "config": {},
        "applies_to": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "Divide revenue evenly among all partners involved"
    },
    "role_weighted_standard": {
        "name": "Role-Weighted - Standard SaaS",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "Implementation (SI)": 0.50,
                "Influence": 0.30,
                "Referral": 0.15,
                "ISV": 0.05
            }
        },
        "applies_to": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "SI gets 50%, Influence 30%, Referral 15%, ISV 5%"
    },
    "time_decay_30d": {
        "name": "Time Decay - 30 Day Half-Life",
        "model_type": AttributionModel.TIME_DECAY,
        "config": {"half_life_days": 30},
        "applies_to": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "More recent partner touches get more credit (30-day half-life)"
    },
    "first_touch_wins": {
        "name": "First Touch Attribution",
        "model_type": AttributionModel.FIRST_TOUCH,
        "config": {},
        "applies_to": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "100% credit to the first partner who touched the deal"
    },
    "last_touch_wins": {
        "name": "Last Touch Attribution",
        "model_type": AttributionModel.LAST_TOUCH,
        "config": {},
        "applies_to": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "100% credit to the last partner who touched before close"
    },
    "activity_weighted": {
        "name": "Activity-Weighted Attribution",
        "model_type": AttributionModel.ACTIVITY_WEIGHTED,
        "config": {"normalize": True},
        "applies_to": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "Partners get credit proportional to their activity (meetings, emails)"
    },
    "u_shaped": {
        "name": "U-Shaped Attribution",
        "model_type": AttributionModel.U_SHAPED,
        "config": {
            "first_touch_weight": 0.4,
            "last_touch_weight": 0.4,
            "middle_weight": 0.2
        },
        "applies_to": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "40% to first touch, 40% to last touch, 20% to middle"
    },
    "enterprise_deals_only": {
        "name": "Role-Weighted - Enterprise Deals Only",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "Implementation (SI)": 0.60,
                "Influence": 0.25,
                "Referral": 0.10,
                "ISV": 0.05
            }
        },
        "applies_to": {"min_value": 100000},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "SI gets 60% on enterprise deals ($100K+)"
    }
}


# ============================================================================
# Validation Functions
# ============================================================================

def validate_rule_config(model_type: AttributionModel, config: Dict[str, Any]) -> tuple:
    """Validate that a rule configuration is valid for its model type."""
    if model_type == AttributionModel.ROLE_WEIGHTED:
        if "weights" not in config:
            return False, "role_weighted requires 'weights' in config"
        if not isinstance(config["weights"], dict):
            return False, "'weights' must be a dictionary"
        if not config["weights"]:
            return False, "'weights' cannot be empty"
        for role, weight in config["weights"].items():
            if not isinstance(weight, (int, float)):
                return False, f"Weight for '{role}' must be numeric"
            if weight < 0:
                return False, f"Weight for '{role}' cannot be negative"

    elif model_type == AttributionModel.TIME_DECAY:
        if "half_life_days" not in config:
            return False, "time_decay requires 'half_life_days' in config"
        if not isinstance(config["half_life_days"], (int, float)):
            return False, "'half_life_days' must be numeric"
        if config["half_life_days"] <= 0:
            return False, "'half_life_days' must be positive"

    elif model_type == AttributionModel.ACTIVITY_WEIGHTED:
        if "normalize" in config and not isinstance(config["normalize"], bool):
            return False, "'normalize' must be boolean"

    elif model_type == AttributionModel.U_SHAPED:
        required_keys = ["first_touch_weight", "last_touch_weight", "middle_weight"]
        for key in required_keys:
            if key not in config:
                return False, f"u_shaped requires '{key}' in config"
            if not isinstance(config[key], (int, float)):
                return False, f"'{key}' must be numeric"
            if config[key] < 0 or config[key] > 1:
                return False, f"'{key}' must be between 0 and 1"

        total = config["first_touch_weight"] + config["last_touch_weight"] + config["middle_weight"]
        if abs(total - 1.0) > 0.001:
            return False, f"u_shaped weights must sum to 1.0 (got {total})"

    return True, None


def validate_touchpoint_for_model(touchpoint: PartnerTouchpoint, model_type: AttributionModel) -> tuple:
    """Validate that a touchpoint has required fields for a given attribution model."""
    if model_type in [AttributionModel.TIME_DECAY, AttributionModel.FIRST_TOUCH,
                      AttributionModel.LAST_TOUCH, AttributionModel.U_SHAPED]:
        if touchpoint.timestamp is None:
            return False, f"{model_type.value} requires touchpoint timestamps"

    if model_type == AttributionModel.ACTIVITY_WEIGHTED:
        if touchpoint.weight is None or touchpoint.weight < 0:
            return False, "activity_weighted requires non-negative touchpoint weights"

    if model_type == AttributionModel.ROLE_WEIGHTED:
        if not touchpoint.role:
            return False, "role_weighted requires touchpoint roles"

    return True, None


# ============================================================================
# Helper Functions
# ============================================================================

def get_rule_template(template_name: str) -> Optional[Dict[str, Any]]:
    """Get a prebuilt rule template by name"""
    return RULE_TEMPLATES.get(template_name)


def list_rule_templates() -> List[Dict[str, Any]]:
    """List all available rule templates with their descriptions"""
    return [
        {
            "name": name,
            "model_type": template["model_type"].value,
            "description": template["description"]
        }
        for name, template in RULE_TEMPLATES.items()
    ]
