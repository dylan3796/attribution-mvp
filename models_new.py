"""
Universal Attribution Data Models
==================================

This module defines the 4-table universal schema that supports
any attribution methodology through configuration, not code.

Core Tables:
1. AttributionTarget - What gets credit (opportunity, consumption event, account)
2. PartnerTouchpoint - Evidence of partner involvement
3. AttributionRule - How to calculate splits (config-driven)
4. AttributionLedger - Immutable output with audit trails

Design Principles:
- Flexibility: Support any attribution model via config
- Immutability: Ledger is append-only (never UPDATE, only INSERT)
- Explainability: Every calculation has an audit trail
- Validation: Rules are validated before execution
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json


# ============================================================================
# Enums and Constants
# ============================================================================

class TargetType(str, Enum):
    """What is being attributed"""
    OPPORTUNITY = "opportunity"          # Salesforce/HubSpot deal
    CONSUMPTION_EVENT = "consumption"    # Usage-based (Databricks, Snowflake)
    ACCOUNT = "account"                  # Account-level attribution
    CUSTOM = "custom"                    # User-defined target type


class RevenueType(str, Enum):
    """Classification of revenue for attribution purposes"""
    NEW_LOGO = "new_logo"                # First contract with a customer
    EXPANSION = "expansion"              # Upsells, cross-sells
    RENEWAL = "renewal"                  # Retention/renewal revenue
    SERVICES = "services"                # One-time professional services
    CONSUMPTION = "consumption"          # Usage-based/metered billing
    CUSTOM = "custom"                    # User-defined revenue type


class ActorType(str, Enum):
    """Types of actors that can receive attribution credit"""
    PARTNER = "partner"                  # External partner (SI, ISV, Referral, etc.)
    CAMPAIGN = "campaign"                # Marketing campaign
    SALES_REP = "sales_rep"              # Internal sales representative
    CHANNEL = "channel"                  # Distribution channel
    CUSTOMER_REFERRAL = "customer_referral"  # Existing customer referral
    EVENT = "event"                      # Events, webinars, conferences
    CONTENT = "content"                  # Content marketing (ebook, blog, etc.)
    CUSTOM = "custom"                    # User-defined actor type


class TouchpointType(str, Enum):
    """How partner involvement is evidenced"""
    # Existing types (backward compatible)
    TAGGED = "tagged"                    # Partner tagged in CRM
    CONTACT_ROLE = "contact_role"        # OpportunityContactRole
    ACTIVITY = "activity"                # Meetings, emails, calls
    REFERRAL = "referral"                # Explicit referral
    MANUAL_OVERRIDE = "manual_override"  # AE manually assigned
    CONSUMPTION_TAG = "consumption_tag"  # Usage data tagged with partner

    # NEW: Additional data source types for flexible measurement
    DEAL_REGISTRATION = "deal_registration"         # Partner-submitted deal reg
    CRM_PARTNER_FIELD = "crm_partner_field"        # Single partner field on opportunity
    MARKETPLACE_TRANSACTION = "marketplace"         # AWS/Azure/GCP marketplace sale
    PARTNER_SELF_REPORTED = "partner_self_reported" # Partner-reported influence
    INTEGRATION_TAG = "integration_tag"             # From integration (Slack, Jira, etc)
    SOURCED_BY = "sourced_by"                       # Opportunity source field


class DataSource(str, Enum):
    """
    Available measurement data sources.

    These define the different systems/methods companies use to track
    partner involvement. Each source has different reliability and
    requires different validation logic.
    """
    DEAL_REGISTRATION = "deal_registration"           # Partner-submitted deal registration
    CRM_OPPORTUNITY_FIELD = "crm_opportunity_field"   # Single partner field in CRM
    TOUCHPOINT_TRACKING = "touchpoint_tracking"       # Activity-based tracking
    MARKETPLACE_TRANSACTIONS = "marketplace_transactions" # AWS/Azure/GCP marketplace
    PARTNER_PORTAL_REPORTING = "partner_portal_reporting" # Partner self-reported
    ACTIVITY_TRACKING = "activity_tracking"           # Meetings, emails, calls
    MANUAL_OVERRIDE = "manual_override"               # Manual assignment by user


class AttributionModel(str, Enum):
    """Attribution calculation methodologies"""
    EQUAL_SPLIT = "equal_split"                  # Divide evenly among all partners
    ROLE_WEIGHTED = "role_weighted"              # Weight by partner role (SI: 60%, Influence: 20%, etc.)
    ACTIVITY_WEIGHTED = "activity_weighted"      # Weight by # of meetings/activities
    TIME_DECAY = "time_decay"                    # More recent touchpoints get more credit
    FIRST_TOUCH = "first_touch"                  # 100% to first partner
    LAST_TOUCH = "last_touch"                    # 100% to last partner
    LINEAR = "linear"                            # Equal credit over time
    U_SHAPED = "u_shaped"                        # 40% first, 40% last, 20% middle
    W_SHAPED = "w_shaped"                        # 30% first, 30% opp creation, 30% close, 10% other
    CUSTOM = "custom"                            # User-defined formula


class SplitConstraint(str, Enum):
    """How to enforce split percentages"""
    MUST_SUM_TO_100 = "must_sum_to_100"         # Splits must add up to 100%
    ALLOW_DOUBLE_COUNTING = "allow_double_counting"  # Splits can exceed 100%
    CAP_AT_100 = "cap_at_100"                   # Each partner capped at 100%, total can exceed
    NO_CONSTRAINT = "no_constraint"             # No validation


SCHEMA_VERSION = "2.0"

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


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AttributionTarget:
    """
    What gets credit - an opportunity, consumption event, or account.

    This is the universal abstraction that works across different SORs:
    - Salesforce Opportunity
    - HubSpot Deal
    - Databricks consumption event
    - Snowflake usage data
    - Custom business events

    Enhanced with revenue type classification for different attribution logic:
    - New Logo: First contract with a customer
    - Expansion: Upsells, cross-sells
    - Renewal: Retention revenue
    - Services: Professional services (one-time)
    - Consumption: Usage-based/metered billing
    """
    id: int
    type: TargetType
    external_id: str                    # SOR's ID (e.g., Salesforce Opp ID)
    value: float                        # $ amount to attribute
    timestamp: datetime                 # When the value was created/closed
    name: Optional[str] = None          # Display name for the target
    revenue_type: Optional[RevenueType] = None  # Classification for attribution rules
    account_id: Optional[str] = None    # Account this target belongs to
    account_name: Optional[str] = None  # Account display name
    metadata: Dict[str, Any] = field(default_factory=dict)  # SOR-specific fields (stage, account_id, etc.)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "external_id": self.external_id,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "revenue_type": self.revenue_type.value if self.revenue_type else None,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class PartnerTouchpoint:
    """
    Evidence of partner involvement with a target.

    Multiple touchpoints per target are common (e.g., SI + Influencer).
    Touchpoints can have different types, roles, weights, and timestamps.

    Enhanced with multi-source measurement support:
    - Tracks which data source created the touchpoint
    - Supports deal registration workflow
    - Enables approval processes for partner-submitted data
    """
    id: int
    partner_id: str                     # Reference to partner (external system or internal ID)
    target_id: int                      # FK to AttributionTarget
    touchpoint_type: TouchpointType
    role: str                           # Partner's role (SI, Influencer, etc.)
    weight: float = 1.0                 # For activity-weighted (# of meetings, etc.)
    timestamp: Optional[datetime] = None  # When partner touched the deal (for time-decay)

    # NEW: Data source tracking (Phase 1.3)
    source: DataSource = DataSource.TOUCHPOINT_TRACKING  # Which system created this touchpoint
    source_id: Optional[str] = None          # External ID in source system (e.g., deal reg ID)
    source_confidence: float = 1.0           # Confidence score (0-1) for data quality

    # NEW: Deal registration fields (Phase 1.3)
    deal_reg_status: Optional[str] = None    # pending/approved/rejected/expired
    deal_reg_submitted_date: Optional[datetime] = None
    deal_reg_approved_date: Optional[datetime] = None

    # NEW: Approval workflow (Phase 1.3)
    requires_approval: bool = False          # Does this touchpoint need manual approval?
    approved_by: Optional[str] = None        # User who approved (if applicable)
    approval_timestamp: Optional[datetime] = None

    metadata: Dict[str, Any] = field(default_factory=dict)  # Context (meeting notes, etc.)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "target_id": self.target_id,
            "touchpoint_type": self.touchpoint_type.value,
            "role": self.role,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            # New source tracking fields
            "source": self.source.value,
            "source_id": self.source_id,
            "source_confidence": self.source_confidence,
            # Deal registration fields
            "deal_reg_status": self.deal_reg_status,
            "deal_reg_submitted_date": self.deal_reg_submitted_date.isoformat() if self.deal_reg_submitted_date else None,
            "deal_reg_approved_date": self.deal_reg_approved_date.isoformat() if self.deal_reg_approved_date else None,
            # Approval workflow fields
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approval_timestamp": self.approval_timestamp.isoformat() if self.approval_timestamp else None,
            # Existing fields
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Touchpoint:
    """
    Universal touchpoint - evidence of ANY actor's involvement with a target.

    This is the generalized version of PartnerTouchpoint that supports
    attribution to any actor type: partners, campaigns, sales reps, channels, etc.

    Key differences from PartnerTouchpoint:
    - actor_type field to distinguish between different contributor types
    - actor_id is generic (partner_id, campaign_id, rep_id, etc.)
    - Supports multi-channel attribution (marketing + partners + sales)
    """
    id: int
    actor_type: ActorType                   # What kind of actor (partner, campaign, sales_rep, etc.)
    actor_id: str                           # Reference to the actor (partner_id, campaign_id, etc.)
    actor_name: Optional[str] = None        # Display name for the actor
    target_id: int                          # FK to AttributionTarget
    touchpoint_type: TouchpointType         # How involvement is evidenced
    role: Optional[str] = None              # Role/category within actor type (e.g., "SI" for partner)
    weight: float = 1.0                     # For activity-weighted attribution
    timestamp: Optional[datetime] = None    # When the touch occurred

    # Source tracking
    source: DataSource = DataSource.TOUCHPOINT_TRACKING
    source_id: Optional[str] = None
    source_confidence: float = 1.0

    # Approval workflow
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor_type": self.actor_type.value,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "target_id": self.target_id,
            "touchpoint_type": self.touchpoint_type.value,
            "role": self.role,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source.value,
            "source_id": self.source_id,
            "source_confidence": self.source_confidence,
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approval_timestamp": self.approval_timestamp.isoformat() if self.approval_timestamp else None,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class DataSourceConfig:
    """
    Configuration for a data source type within a measurement workflow.

    Defines how a specific data source should be used for attribution:
    - Priority for source selection (lower number = higher priority)
    - Whether to auto-create touchpoints from this source
    - Validation requirements
    - Source-specific configuration

    Example configs:
    - Deal Registration: {"require_approval": True, "expiry_days": 90}
    - CRM Field: {"field_name": "Partner__c", "role_field": "Partner_Role__c"}
    - Marketplace: {"platform": "aws", "attribution_percentage": 1.0}
    - Touchpoints: {"min_activity_count": 3, "role_weights": {...}}
    """
    source_type: DataSource
    enabled: bool = True
    priority: int = 100                      # Lower = higher priority (1 beats 100)
    auto_create_touchpoints: bool = True     # Auto-create touchpoints from this source
    requires_validation: bool = False        # Require manual approval before attribution
    config: Dict[str, Any] = field(default_factory=dict)  # Source-specific settings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "auto_create_touchpoints": self.auto_create_touchpoints,
            "requires_validation": self.requires_validation,
            "config": json.dumps(self.config)
        }


@dataclass
class MeasurementWorkflow:
    """
    Defines HOW a company measures partner contribution.

    This is the key to platform flexibility - instead of hardcoding measurement
    methodologies, each company configures their own workflow that specifies:
    - Which data sources to use (deal reg, CRM fields, touchpoints, etc.)
    - Priority ordering (which source wins if multiple have data)
    - Conflict resolution (priority-based, merge/weighted, manual review)
    - Fallback strategy (what to do if primary source has no data)
    - Deal type scoping (different workflows for different deal segments)

    Example Workflows:
    - "Deal Reg Primary": Use deal reg if exists, else touchpoints (priority)
    - "Marketplace Only": 100% to marketplace partner for marketplace deals
    - "Hybrid SI+Influence": 80% deal reg + 20% influence touchpoints (merge)
    - "CRM with Fallback": Use Partner__c field if set, else calculate from activities
    """
    id: int
    company_id: str                     # Which organization owns this workflow
    name: str
    description: str

    # Which data sources and their priority
    data_sources: List[DataSourceConfig] = field(default_factory=list)

    # Conflict resolution strategy when multiple sources have data
    conflict_resolution: str = "priority"    # priority/merge/manual_review

    # Fallback logic when primary source has no data
    fallback_strategy: str = "next_priority" # next_priority/equal_split/manual

    # Deal type scoping (filters to determine when this workflow applies)
    applies_to: Dict[str, Any] = field(default_factory=dict)

    # Is this the primary methodology for reporting/payouts?
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
            "applies_to": json.dumps(self.applies_to),
            "is_primary": self.is_primary,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class AttributionRule:
    """
    Configuration-driven rule for calculating attribution splits.

    This is the key to flexibility - instead of hardcoding logic,
    we store rules as JSON config that the engine interprets.

    Example rule configs:
    - Role-weighted: {"weights": {"SI": 0.6, "Influence": 0.2, "Referral": 0.2}}
    - Time-decay: {"half_life_days": 30}
    - Activity-weighted: {"normalize": True}
    - First-touch: {}
    """
    id: int
    name: str
    model_type: AttributionModel
    config: Dict[str, Any]              # Model-specific configuration
    applies_to: Dict[str, Any] = field(default_factory=dict)  # Filters (target_type, metadata conditions)
    priority: int = 100                 # If multiple rules match, use highest priority
    split_constraint: SplitConstraint = SplitConstraint.MUST_SUM_TO_100
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None    # User who created the rule

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_type": self.model_type.value,
            "config": json.dumps(self.config),
            "applies_to": json.dumps(self.applies_to),
            "priority": self.priority,
            "split_constraint": self.split_constraint.value,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }

    def matches_target(self, target: AttributionTarget) -> bool:
        """Check if this rule applies to a given target"""
        if not self.applies_to:
            return True  # No filters = applies to all

        # Check target type filter
        if "target_type" in self.applies_to:
            if target.type.value != self.applies_to["target_type"]:
                return False

        # Check metadata filters (e.g., stage, account_id, value ranges)
        if "metadata" in self.applies_to:
            for key, expected_value in self.applies_to["metadata"].items():
                if key not in target.metadata:
                    return False
                if target.metadata[key] != expected_value:
                    return False

        # Check value range filters
        if "min_value" in self.applies_to:
            if target.value < self.applies_to["min_value"]:
                return False
        if "max_value" in self.applies_to:
            if target.value > self.applies_to["max_value"]:
                return False

        return True


@dataclass
class LedgerEntry:
    """
    Immutable attribution result - output of the calculation engine.

    This is the source of truth for "Partner X gets $Y from Target Z".
    Ledger is append-only - never UPDATE, only INSERT.

    Audit trail captures:
    - Which rule was used
    - When it was calculated
    - Who triggered the calculation (human or automated)
    - The calculation steps (for explainability)
    """
    id: int
    target_id: int                      # FK to AttributionTarget
    partner_id: str
    attributed_value: float             # $ amount attributed to this partner
    split_percentage: float             # % of target value (0.0 to 1.0, or >1.0 if double-counting)
    rule_id: int                        # FK to AttributionRule
    calculation_timestamp: datetime
    override_by: Optional[str] = None   # User who manually overrode (if applicable)
    override_reason: Optional[str] = None  # Reason for manual override (required for audit compliance)
    audit_trail: Dict[str, Any] = field(default_factory=dict)  # Calculation steps, filters applied, etc.
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_id": self.target_id,
            "partner_id": self.partner_id,
            "attributed_value": self.attributed_value,
            "split_percentage": self.split_percentage,
            "rule_id": self.rule_id,
            "calculation_timestamp": self.calculation_timestamp.isoformat(),
            "override_by": self.override_by,
            "audit_trail": json.dumps(self.audit_trail),
            "created_at": self.created_at.isoformat()
        }

    def explain(self) -> str:
        """Human-readable explanation of this ledger entry"""
        rule_name = self.audit_trail.get("rule_name", "Unknown")
        model_type = self.audit_trail.get("model_type", "Unknown")

        explanation = (
            f"Partner {self.partner_id} received ${self.attributed_value:,.2f} "
            f"({self.split_percentage:.1%} split) from Target {self.target_id} "
            f"using '{rule_name}' rule ({model_type} model)."
        )

        # Add calculation details if available
        if "calculation_steps" in self.audit_trail:
            explanation += f"\n\nCalculation steps:\n{self.audit_trail['calculation_steps']}"

        return explanation


# ============================================================================
# Rule Templates (Prebuilt Rules for Common Scenarios)
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
        "config": {
            "half_life_days": 30
        },
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
        "config": {
            "normalize": True
        },
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
        "applies_to": {
            "min_value": 100000  # Only apply to deals >$100K
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "description": "SI gets 60% on enterprise deals ($100K+)"
    }
}


# ============================================================================
# Validation Functions
# ============================================================================

def validate_rule_config(model_type: AttributionModel, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that a rule configuration is valid for its model type.

    Returns: (is_valid, error_message)
    """

    if model_type == AttributionModel.ROLE_WEIGHTED:
        if "weights" not in config:
            return False, "role_weighted requires 'weights' in config"
        if not isinstance(config["weights"], dict):
            return False, "'weights' must be a dictionary"
        if not config["weights"]:
            return False, "'weights' cannot be empty"
        # Check that weights are numeric and non-negative
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
        # Optional: normalize parameter
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

        # Check that weights sum to 1.0 (with small tolerance for floating point)
        total = config["first_touch_weight"] + config["last_touch_weight"] + config["middle_weight"]
        if abs(total - 1.0) > 0.001:
            return False, f"u_shaped weights must sum to 1.0 (got {total})"

    # Other models (equal_split, first_touch, last_touch, linear) have no config requirements

    return True, None


def validate_touchpoint_for_model(touchpoint: PartnerTouchpoint, model_type: AttributionModel) -> tuple[bool, Optional[str]]:
    """
    Validate that a touchpoint has required fields for a given attribution model.

    Returns: (is_valid, error_message)
    """

    if model_type in [AttributionModel.TIME_DECAY, AttributionModel.FIRST_TOUCH, AttributionModel.LAST_TOUCH, AttributionModel.U_SHAPED]:
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


# ============================================================================
# Period Management
# ============================================================================

class PeriodType(str, Enum):
    """Type of attribution period"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class PeriodStatus(str, Enum):
    """Status of an attribution period"""
    OPEN = "open"            # Active, calculations can be modified
    CLOSED = "closed"        # Closed for reporting, can still recalculate
    LOCKED = "locked"        # Fully locked, no changes allowed


@dataclass
class AttributionPeriod:
    """
    Represents a time period for attribution calculations.

    Periods allow companies to:
    - Close attribution calculations for a time period
    - Lock historical data to prevent retroactive changes
    - Generate period-based reports
    - Track period-over-period performance
    """
    id: int
    organization_id: str
    name: str                        # e.g., "Q1 2024", "January 2024"
    period_type: PeriodType
    start_date: datetime
    end_date: datetime
    status: PeriodStatus = PeriodStatus.OPEN

    # Metadata
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None

    # Attribution summary (calculated when closed)
    total_revenue: float = 0.0
    total_deals: int = 0
    total_partners: int = 0

    # Audit trail
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    notes: Optional[str] = None

    def is_open(self) -> bool:
        """Check if period is open for modifications"""
        return self.status == PeriodStatus.OPEN

    def is_closed(self) -> bool:
        """Check if period is closed"""
        return self.status in [PeriodStatus.CLOSED, PeriodStatus.LOCKED]

    def is_locked(self) -> bool:
        """Check if period is locked"""
        return self.status == PeriodStatus.LOCKED

    def can_recalculate(self) -> bool:
        """Check if attribution can be recalculated"""
        return self.status != PeriodStatus.LOCKED

    def contains_date(self, check_date: datetime) -> bool:
        """Check if a date falls within this period"""
        return self.start_date <= check_date <= self.end_date
