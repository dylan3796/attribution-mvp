"""
Prebuilt Attribution Rule Templates
====================================

Common attribution templates that users can apply with one click.

Templates are organized by:
- Industry (SaaS, Cloud Infrastructure, Consulting)
- Deal size (SMB, Mid-Market, Enterprise)
- Partner program maturity (Early-stage, Growth, Mature)
"""

from typing import Dict, List, Any, Optional
from models import RULE_TEMPLATES, AttributionModel, SplitConstraint


# ============================================================================
# Template Categories
# ============================================================================

TEMPLATES_BY_CATEGORY = {
    "simple": [
        "equal_split_all",
        "first_touch_wins",
        "last_touch_wins"
    ],

    "saas_standard": [
        "role_weighted_standard",
        "time_decay_30d",
        "activity_weighted"
    ],

    "enterprise": [
        "enterprise_deals_only",
        "u_shaped"
    ],

    "channel_heavy": [
        "role_weighted_standard",
        "first_touch_wins"
    ]
}


# ============================================================================
# Industry-Specific Templates
# ============================================================================

INDUSTRY_TEMPLATES = {
    "saas_b2b": {
        "name": "SaaS B2B Standard",
        "description": "Common attribution for SaaS companies with SI + influence partners",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "Implementation (SI)": 0.50,
                "Influence": 0.30,
                "Referral": 0.15,
                "ISV": 0.05
            }
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "cloud_infrastructure": {
        "name": "Cloud Infrastructure (Consumption-Based)",
        "description": "Databricks/Snowflake style - time-decay favoring recent partner engagement",
        "model_type": AttributionModel.TIME_DECAY,
        "config": {
            "half_life_days": 45  # Longer sales cycles
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "consulting_services": {
        "name": "Consulting/Services",
        "description": "Activity-based attribution - who did the work gets the credit",
        "model_type": AttributionModel.ACTIVITY_WEIGHTED,
        "config": {
            "normalize": True
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "channel_first": {
        "name": "Channel-First (Resellers)",
        "description": "Resellers/channel partners get majority credit",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "Reseller": 0.70,
                "Implementation (SI)": 0.20,
                "Influence": 0.10
            }
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "technology_partnership": {
        "name": "Technology Partnership (ISV Focus)",
        "description": "ISV/tech partners get higher weight",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "ISV": 0.50,
                "Implementation (SI)": 0.30,
                "Influence": 0.20
            }
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    }
}


# ============================================================================
# Deal Size Templates
# ============================================================================

DEAL_SIZE_TEMPLATES = {
    "smb_velocity": {
        "name": "SMB Velocity Deals (<$25K)",
        "description": "Fast-moving SMB deals - first touch or last touch",
        "model_type": AttributionModel.FIRST_TOUCH,
        "config": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {
            "max_value": 25000
        }
    },

    "mid_market": {
        "name": "Mid-Market ($25K-$100K)",
        "description": "Standard role-weighted for mid-market",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "Implementation (SI)": 0.50,
                "Influence": 0.35,
                "Referral": 0.15
            }
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {
            "min_value": 25000,
            "max_value": 100000
        }
    },

    "enterprise": {
        "name": "Enterprise ($100K+)",
        "description": "SI-heavy for complex enterprise deals",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "Implementation (SI)": 0.60,
                "Influence": 0.25,
                "Referral": 0.10,
                "ISV": 0.05
            }
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {
            "min_value": 100000
        }
    },

    "strategic": {
        "name": "Strategic Deals ($1M+)",
        "description": "Multi-touch attribution for complex strategic deals",
        "model_type": AttributionModel.U_SHAPED,
        "config": {
            "first_touch_weight": 0.35,
            "last_touch_weight": 0.35,
            "middle_weight": 0.30
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {
            "min_value": 1000000
        }
    }
}


# ============================================================================
# Partner Program Maturity Templates
# ============================================================================

MATURITY_TEMPLATES = {
    "early_stage": {
        "name": "Early-Stage Partner Program",
        "description": "Simple equal split - still figuring out attribution",
        "model_type": AttributionModel.EQUAL_SPLIT,
        "config": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "growth_stage": {
        "name": "Growth-Stage Partner Program",
        "description": "Role-based with standard weights",
        "model_type": AttributionModel.ROLE_WEIGHTED,
        "config": {
            "weights": {
                "Implementation (SI)": 0.50,
                "Influence": 0.30,
                "Referral": 0.20
            }
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "mature": {
        "name": "Mature Partner Program",
        "description": "Sophisticated multi-touch with time-decay",
        "model_type": AttributionModel.TIME_DECAY,
        "config": {
            "half_life_days": 30
        },
        "split_constraint": SplitConstraint.ALLOW_DOUBLE_COUNTING,  # Allow partners to accumulate credit
        "applies_to": {}
    }
}


# ============================================================================
# Use Case Templates
# ============================================================================

USE_CASE_TEMPLATES = {
    "partner_sourcing": {
        "name": "Partner Sourcing (First-Touch)",
        "description": "100% credit to partner who sourced the deal",
        "model_type": AttributionModel.FIRST_TOUCH,
        "config": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "co_sell": {
        "name": "Co-Sell (Equal Split)",
        "description": "Partner and internal team split evenly",
        "model_type": AttributionModel.EQUAL_SPLIT,
        "config": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "marketplace": {
        "name": "Marketplace Transactions",
        "description": "Last-touch attribution for marketplace deals",
        "model_type": AttributionModel.LAST_TOUCH,
        "config": {},
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    },

    "partner_influenced": {
        "name": "Partner-Influenced (Activity-Based)",
        "description": "Credit based on partner engagement level",
        "model_type": AttributionModel.ACTIVITY_WEIGHTED,
        "config": {
            "normalize": True
        },
        "split_constraint": SplitConstraint.MUST_SUM_TO_100,
        "applies_to": {}
    }
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a template by ID from any category.

    Args:
        template_id: Template identifier

    Returns:
        Template config dict or None
    """
    # Check base templates
    if template_id in RULE_TEMPLATES:
        return _convert_template(RULE_TEMPLATES[template_id])

    # Check industry templates
    if template_id in INDUSTRY_TEMPLATES:
        return _convert_template(INDUSTRY_TEMPLATES[template_id])

    # Check deal size templates
    if template_id in DEAL_SIZE_TEMPLATES:
        return _convert_template(DEAL_SIZE_TEMPLATES[template_id])

    # Check maturity templates
    if template_id in MATURITY_TEMPLATES:
        return _convert_template(MATURITY_TEMPLATES[template_id])

    # Check use case templates
    if template_id in USE_CASE_TEMPLATES:
        return _convert_template(USE_CASE_TEMPLATES[template_id])

    return None


def list_templates(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all available templates, optionally filtered by category.

    Args:
        category: "simple", "saas_standard", "enterprise", "industry", "deal_size", "maturity", "use_case", or None for all

    Returns:
        List of template metadata dicts
    """
    templates = []

    if category is None or category == "base":
        for template_id, template in RULE_TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "model_type": template["model_type"].value,
                "category": "base"
            })

    if category is None or category == "industry":
        for template_id, template in INDUSTRY_TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "model_type": template["model_type"].value,
                "category": "industry"
            })

    if category is None or category == "deal_size":
        for template_id, template in DEAL_SIZE_TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "model_type": template["model_type"].value,
                "category": "deal_size"
            })

    if category is None or category == "maturity":
        for template_id, template in MATURITY_TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "model_type": template["model_type"].value,
                "category": "maturity"
            })

    if category is None or category == "use_case":
        for template_id, template in USE_CASE_TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "model_type": template["model_type"].value,
                "category": "use_case"
            })

    return templates


def recommend_template(
    company_size: str = "growth",
    industry: str = "saas",
    partner_program_maturity: str = "growth"
) -> str:
    """
    Recommend a template based on company profile.

    Args:
        company_size: "startup", "growth", "enterprise"
        industry: "saas", "cloud", "consulting", "channel"
        partner_program_maturity: "early", "growth", "mature"

    Returns:
        Recommended template ID
    """

    # Early-stage companies
    if partner_program_maturity == "early":
        return "early_stage"

    # Mature programs with sophisticated needs
    if partner_program_maturity == "mature":
        return "mature"

    # Industry-specific recommendations
    if industry == "cloud":
        return "cloud_infrastructure"
    elif industry == "consulting":
        return "consulting_services"
    elif industry == "channel":
        return "channel_first"

    # Default to SaaS B2B standard for growth companies
    return "saas_b2b"


def _convert_template(template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert template to standard format (handle enums).
    """
    return {
        "name": template["name"],
        "description": template.get("description", ""),
        "model_type": template["model_type"].value if hasattr(template["model_type"], "value") else template["model_type"],
        "config": template["config"],
        "split_constraint": template["split_constraint"].value if hasattr(template["split_constraint"], "value") else template["split_constraint"],
        "applies_to": template.get("applies_to", {})
    }


# ============================================================================
# Template Comparison
# ============================================================================

def compare_templates(template_ids: List[str]) -> Dict[str, Any]:
    """
    Compare multiple templates side-by-side.

    Args:
        template_ids: List of template IDs to compare

    Returns:
        Comparison dict with template details
    """
    comparison = {
        "templates": [],
        "differences": []
    }

    templates = [get_template(tid) for tid in template_ids if get_template(tid)]

    for template in templates:
        comparison["templates"].append({
            "name": template["name"],
            "model_type": template["model_type"],
            "config": template["config"],
            "constraint": template["split_constraint"]
        })

    # Highlight key differences
    if len(templates) > 1:
        models = set(t["model_type"] for t in templates)
        if len(models) > 1:
            comparison["differences"].append(f"Different models: {', '.join(models)}")

        constraints = set(t["split_constraint"] for t in templates)
        if len(constraints) > 1:
            comparison["differences"].append(f"Different constraints: {', '.join(constraints)}")

    return comparison
