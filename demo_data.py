"""
Demo Data Generator
===================

Generate realistic sample data for attribution demos.

Creates:
- 10 realistic opportunities (SaaS B2B deals)
- 25 partner touchpoints across different roles
- 3 attribution rules (showing different methodologies)
- Pre-calculated ledger entries
"""

from datetime import datetime, timedelta
import random
from typing import List, Tuple
from models_new import (
    AttributionTarget, PartnerTouchpoint, AttributionRule, LedgerEntry,
    TargetType, TouchpointType, AttributionModel, SplitConstraint
)
from attribution_engine import AttributionEngine


# ============================================================================
# Demo Company & Partner Names
# ============================================================================

DEMO_COMPANIES = [
    "Acme Corp", "TechStart Inc", "CloudScale Systems", "DataFlow Solutions",
    "SecureNet Ltd", "InnovateCo", "GlobalTech Partners", "FutureOps Inc",
    "SmartData Corp", "AgileWorks LLC"
]

DEMO_PARTNER_NAMES = {
    "P001": "Deloitte Digital",
    "P002": "Accenture Cloud First",
    "P003": "PartnerHub Consulting",
    "P004": "TechAlliance Group",
    "P005": "CloudExperts SI",
    "P006": "DataBridge Partners",
    "P007": "Integration Masters"
}

DEMO_PARTNER_ROLES = {
    "P001": "Implementation (SI)",
    "P002": "Implementation (SI)",
    "P003": "Influence",
    "P004": "Influence",
    "P005": "Referral",
    "P006": "ISV",
    "P007": "Implementation (SI)"
}


# ============================================================================
# Demo Data Generation
# ============================================================================

def generate_demo_targets(num_targets: int = 10) -> List[AttributionTarget]:
    """
    Generate realistic opportunity targets.

    Deal sizes follow typical SaaS B2B distribution:
    - 40% SMB ($10K-$25K)
    - 40% Mid-Market ($25K-$100K)
    - 15% Enterprise ($100K-$500K)
    - 5% Strategic ($500K-$2M)

    Stage distribution:
    - 60% Closed Won
    - 10% Closed Lost
    - 30% Open Pipeline (Discovery, Qualification, Proposal, Negotiation)
    """
    targets = []
    base_date = datetime.now() - timedelta(days=90)  # Deals from last 90 days

    for i in range(num_targets):
        # Determine deal size tier
        rand = random.random()
        if rand < 0.40:  # SMB
            value = random.randint(10000, 25000)
        elif rand < 0.80:  # Mid-Market
            value = random.randint(25000, 100000)
        elif rand < 0.95:  # Enterprise
            value = random.randint(100000, 500000)
        else:  # Strategic
            value = random.randint(500000, 2000000)

        # Random close date within last 90 days (or future for open pipeline)
        days_ago = random.randint(0, 90)
        close_date = base_date + timedelta(days=days_ago)

        # Determine stage (60% Closed Won, 10% Closed Lost, 30% Open)
        stage_rand = random.random()
        if stage_rand < 0.60:  # 60% Closed Won
            stage = "Closed Won"
            # Closed deals use the close_date as-is
        elif stage_rand < 0.70:  # 10% Closed Lost
            stage = "Closed Lost"
            # Closed deals use the close_date as-is
        else:  # 30% Open Pipeline
            stage = random.choice([
                "Discovery",
                "Qualification",
                "Proposal",
                "Negotiation"
            ])
            # Open deals have future expected close dates
            close_date = datetime.now() + timedelta(days=random.randint(15, 60))

        # Created date: 30-90 days before close date
        days_before_close = random.randint(30, 90)
        created_date = close_date - timedelta(days=days_before_close)

        target = AttributionTarget(
            id=i + 1,
            type=TargetType.OPPORTUNITY,
            external_id=f"OPP-{1000 + i}",
            value=float(value),
            timestamp=close_date,
            metadata={
                "account_name": DEMO_COMPANIES[i % len(DEMO_COMPANIES)],
                "account_id": f"ACC-{200 + (i % len(DEMO_COMPANIES))}",
                "stage": stage,
                "created_date": created_date.isoformat(),
                "is_won": stage == "Closed Won",
                "is_closed": stage in ["Closed Won", "Closed Lost"],
                "region": random.choice(["North America", "EMEA", "APAC"]),
                "deal_type": random.choice(["New Business", "Expansion", "Renewal"])
            }
        )
        targets.append(target)

    return targets


def generate_demo_touchpoints(targets: List[AttributionTarget]) -> List[PartnerTouchpoint]:
    """
    Generate realistic partner touchpoints for each target.

    Touchpoint patterns:
    - Small deals: 1-3 touchpoints (simple sales cycle)
    - Medium deals: 2-4 touchpoints
    - Large deals: 3-6 touchpoints (complex, multi-partner)
    """
    touchpoints = []
    touchpoint_id = 1

    for target in targets:
        # Determine number of touchpoints based on deal size
        if target.value < 25000:
            num_touches = random.randint(1, 3)
        elif target.value < 100000:
            num_touches = random.randint(2, 4)
        else:
            num_touches = random.randint(3, 6)

        # Select random partners (no duplicates for this target)
        partner_ids = random.sample(list(DEMO_PARTNER_NAMES.keys()), num_touches)

        # Generate touchpoints spread over time before close date
        for idx, partner_id in enumerate(partner_ids):
            # First touch is earliest, last touch is closest to close date
            days_before_close = random.randint(
                (num_touches - idx - 1) * 10,  # Min days before
                (num_touches - idx) * 15        # Max days before
            )
            touchpoint_date = target.timestamp - timedelta(days=days_before_close)

            # Activity weight (1-10 meetings/activities)
            activity_count = random.randint(1, 10)

            touchpoint = PartnerTouchpoint(
                id=touchpoint_id,
                partner_id=partner_id,
                target_id=target.id,
                touchpoint_type=TouchpointType.ACTIVITY,
                role=DEMO_PARTNER_ROLES[partner_id],
                weight=float(activity_count),
                timestamp=touchpoint_date,
                metadata={
                    "partner_name": DEMO_PARTNER_NAMES[partner_id],
                    "activity_count": activity_count,
                    "activity_types": random.choice([
                        "Initial Meeting, Discovery Call",
                        "Demo, Technical Deep Dive, Proposal",
                        "Executive Briefing, POC, Contract Review",
                        "Whiteboarding Session, Architecture Review"
                    ])
                }
            )
            touchpoints.append(touchpoint)
            touchpoint_id += 1

    return touchpoints


def generate_demo_rules() -> List[AttributionRule]:
    """
    Generate 3 attribution rules showing different methodologies.
    """
    rules = [
        AttributionRule(
            id=1,
            name="SaaS B2B Standard (Role-Weighted)",
            model_type=AttributionModel.ROLE_WEIGHTED,
            config={
                "weights": {
                    "Implementation (SI)": 0.50,
                    "Influence": 0.30,
                    "Referral": 0.15,
                    "ISV": 0.05
                }
            },
            applies_to={},  # Applies to all deals
            priority=100,
            split_constraint=SplitConstraint.MUST_SUM_TO_100
        ),
        AttributionRule(
            id=2,
            name="Enterprise Deals Only (SI-Heavy)",
            model_type=AttributionModel.ROLE_WEIGHTED,
            config={
                "weights": {
                    "Implementation (SI)": 0.60,
                    "Influence": 0.25,
                    "Referral": 0.10,
                    "ISV": 0.05
                }
            },
            applies_to={"min_value": 100000},  # Only for $100K+ deals
            priority=200,  # Higher priority than default rule
            split_constraint=SplitConstraint.MUST_SUM_TO_100
        ),
        AttributionRule(
            id=3,
            name="Time Decay (30-day half-life)",
            model_type=AttributionModel.TIME_DECAY,
            config={"half_life_days": 30},
            applies_to={},
            priority=50,  # Lower priority (only used if manually selected)
            split_constraint=SplitConstraint.MUST_SUM_TO_100
        )
    ]

    return rules


def calculate_demo_ledger(
    targets: List[AttributionTarget],
    touchpoints: List[PartnerTouchpoint],
    rules: List[AttributionRule]
) -> List[LedgerEntry]:
    """
    Pre-calculate attribution ledger entries using the attribution engine.
    """
    engine = AttributionEngine()
    all_entries = []

    for target in targets:
        # Get touchpoints for this target
        target_touchpoints = [tp for tp in touchpoints if tp.target_id == target.id]

        # Select best matching rule
        matching_rules = []
        for rule in rules:
            applies_to = rule.applies_to

            # Check if rule applies to this target
            if "min_value" in applies_to and target.value < applies_to["min_value"]:
                continue
            if "max_value" in applies_to and target.value > applies_to["max_value"]:
                continue

            matching_rules.append(rule)

        # Use highest priority rule
        if matching_rules:
            selected_rule = max(matching_rules, key=lambda r: r.priority)
        else:
            selected_rule = rules[0]  # Default to first rule

        # Calculate attribution
        entries = engine.calculate(target, target_touchpoints, selected_rule)
        all_entries.extend(entries)

    return all_entries


def generate_complete_demo_data() -> Tuple[
    List[AttributionTarget],
    List[PartnerTouchpoint],
    List[AttributionRule],
    List[LedgerEntry]
]:
    """
    Generate complete demo dataset with all components.

    Returns:
        (targets, touchpoints, rules, ledger_entries)
    """
    random.seed(42)  # Consistent demo data

    targets = generate_demo_targets(num_targets=10)
    touchpoints = generate_demo_touchpoints(targets)
    rules = generate_demo_rules()
    ledger = calculate_demo_ledger(targets, touchpoints, rules)

    return targets, touchpoints, rules, ledger


def get_demo_data_summary(
    targets: List[AttributionTarget],
    touchpoints: List[PartnerTouchpoint],
    rules: List[AttributionRule],
    ledger: List[LedgerEntry]
) -> dict:
    """
    Generate summary statistics for demo data.
    """
    total_revenue = sum(t.value for t in targets)
    total_attributed = sum(e.attributed_value for e in ledger)

    # Partner breakdown
    partner_revenue = {}
    for entry in ledger:
        partner_id = entry.partner_id
        partner_name = DEMO_PARTNER_NAMES.get(partner_id, partner_id)
        partner_revenue[partner_name] = partner_revenue.get(partner_name, 0) + entry.attributed_value

    return {
        "num_targets": len(targets),
        "num_touchpoints": len(touchpoints),
        "num_rules": len(rules),
        "num_ledger_entries": len(ledger),
        "total_revenue": total_revenue,
        "total_attributed": total_attributed,
        "attribution_accuracy": (total_attributed / total_revenue * 100) if total_revenue > 0 else 0,
        "top_partners": sorted(partner_revenue.items(), key=lambda x: x[1], reverse=True)[:5],
        "date_range": (
            min(t.timestamp for t in targets).strftime("%Y-%m-%d"),
            max(t.timestamp for t in targets).strftime("%Y-%m-%d")
        )
    }


# ============================================================================
# CLI Usage (Optional)
# ============================================================================

if __name__ == "__main__":
    print("🎲 Generating demo data...\n")

    targets, touchpoints, rules, ledger = generate_complete_demo_data()
    summary = get_demo_data_summary(targets, touchpoints, rules, ledger)

    print(f"✅ Generated demo dataset:")
    print(f"   - {summary['num_targets']} opportunities")
    print(f"   - {summary['num_touchpoints']} partner touchpoints")
    print(f"   - {summary['num_rules']} attribution rules")
    print(f"   - {summary['num_ledger_entries']} ledger entries")
    print(f"\n💰 Revenue:")
    print(f"   - Total: ${summary['total_revenue']:,.2f}")
    print(f"   - Attributed: ${summary['total_attributed']:,.2f}")
    print(f"   - Accuracy: {summary['attribution_accuracy']:.1f}%")
    print(f"\n📅 Date Range: {summary['date_range'][0]} to {summary['date_range'][1]}")
    print(f"\n🏆 Top 5 Partners by Attributed Revenue:")
    for partner_name, revenue in summary['top_partners']:
        print(f"   - {partner_name}: ${revenue:,.2f}")
