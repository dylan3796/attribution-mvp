"""
Universal Attribution Calculation Engine
=========================================

This engine calculates attribution splits for any methodology by:
1. Filtering touchpoints based on rule criteria
2. Calculating splits using model-specific logic
3. Enforcing split constraints
4. Generating audit trails for explainability

All calculation methods return LedgerEntry objects but DON'T write to the database.
That's the caller's responsibility (separation of concerns).
"""

import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from models_new import (
    AttributionTarget,
    PartnerTouchpoint,
    AttributionRule,
    LedgerEntry,
    AttributionModel,
    SplitConstraint,
    validate_touchpoint_for_model
)


class AttributionEngine:
    """
    Calculate attribution splits using configuration-driven rules.

    This engine is stateless - it takes inputs (target, touchpoints, rule)
    and returns outputs (ledger entries). No database dependencies.
    """

    def calculate(
        self,
        target: AttributionTarget,
        touchpoints: List[PartnerTouchpoint],
        rule: AttributionRule,
        override_by: Optional[str] = None
    ) -> List[LedgerEntry]:
        """
        Main entry point: Calculate attribution for a target.

        Args:
            target: What's being attributed (opportunity, consumption event, etc.)
            touchpoints: Evidence of partner involvement
            rule: Configuration-driven rule
            override_by: User who manually triggered this (if applicable)

        Returns:
            List of LedgerEntry objects (one per partner getting credit)
        """

        # Step 1: Filter touchpoints (rule may have filters)
        filtered_touchpoints = self._filter_touchpoints(touchpoints, rule)

        if not filtered_touchpoints:
            # No partners match the rule criteria - return empty ledger
            return []

        # Step 2: Validate touchpoints have required fields for this model
        for tp in filtered_touchpoints:
            is_valid, error = validate_touchpoint_for_model(tp, rule.model_type)
            if not is_valid:
                # Skip touchpoints that don't have required data
                # (In production, you'd log this warning)
                filtered_touchpoints = [t for t in filtered_touchpoints if t.id != tp.id]

        if not filtered_touchpoints:
            return []

        # Step 3: Calculate splits using model-specific logic
        splits = self._calculate_splits(target, filtered_touchpoints, rule)

        # Step 4: Enforce split constraints
        splits = self._enforce_constraints(splits, rule.split_constraint)

        # Step 5: Generate ledger entries with audit trails
        ledger_entries = self._generate_ledger_entries(
            target=target,
            splits=splits,
            rule=rule,
            touchpoints=filtered_touchpoints,
            override_by=override_by
        )

        return ledger_entries

    def _filter_touchpoints(
        self,
        touchpoints: List[PartnerTouchpoint],
        rule: AttributionRule
    ) -> List[PartnerTouchpoint]:
        """
        Filter touchpoints based on rule criteria.

        Rules can filter by:
        - touchpoint_type (e.g., only "tagged" touchpoints)
        - role (e.g., only "Implementation (SI)" partners)
        - metadata conditions
        """
        filtered = touchpoints

        if "filters" in rule.config:
            filters = rule.config["filters"]

            if "touchpoint_types" in filters:
                allowed_types = filters["touchpoint_types"]
                filtered = [tp for tp in filtered if tp.touchpoint_type.value in allowed_types]

            if "roles" in filters:
                allowed_roles = filters["roles"]
                filtered = [tp for tp in filtered if tp.role in allowed_roles]

            if "exclude_roles" in filters:
                excluded_roles = filters["exclude_roles"]
                filtered = [tp for tp in filtered if tp.role not in excluded_roles]

            if "min_weight" in filters:
                min_weight = filters["min_weight"]
                filtered = [tp for tp in filtered if tp.weight >= min_weight]

        return filtered

    def _calculate_splits(
        self,
        target: AttributionTarget,
        touchpoints: List[PartnerTouchpoint],
        rule: AttributionRule
    ) -> Dict[str, float]:
        """
        Calculate split percentages using the rule's model type.

        Returns: {partner_id: split_percentage}
        """

        model_type = rule.model_type

        if model_type == AttributionModel.EQUAL_SPLIT:
            return self._equal_split(touchpoints)

        elif model_type == AttributionModel.ROLE_WEIGHTED:
            return self._role_weighted(touchpoints, rule.config)

        elif model_type == AttributionModel.ACTIVITY_WEIGHTED:
            return self._activity_weighted(touchpoints, rule.config)

        elif model_type == AttributionModel.TIME_DECAY:
            return self._time_decay(target, touchpoints, rule.config)

        elif model_type == AttributionModel.FIRST_TOUCH:
            return self._first_touch(touchpoints)

        elif model_type == AttributionModel.LAST_TOUCH:
            return self._last_touch(touchpoints)

        elif model_type == AttributionModel.LINEAR:
            return self._linear(touchpoints)

        elif model_type == AttributionModel.U_SHAPED:
            return self._u_shaped(touchpoints, rule.config)

        else:
            # Default to equal split if model not recognized
            return self._equal_split(touchpoints)

    # ========================================================================
    # Calculation Methods (one per attribution model)
    # ========================================================================

    def _equal_split(self, touchpoints: List[PartnerTouchpoint]) -> Dict[str, float]:
        """
        Divide 100% evenly among all partners.

        Example: 3 partners → each gets 33.33%
        """
        if not touchpoints:
            return {}

        split_pct = 1.0 / len(touchpoints)
        return {tp.partner_id: split_pct for tp in touchpoints}

    def _role_weighted(
        self,
        touchpoints: List[PartnerTouchpoint],
        config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Weight by partner role using configured weights.

        Config example:
        {
            "weights": {
                "Implementation (SI)": 0.6,
                "Influence": 0.3,
                "Referral": 0.1
            }
        }

        If a partner's role isn't in the config, use weight of 1.0.
        """
        weights_config = config.get("weights", {})

        # Calculate total weight
        total_weight = sum(
            weights_config.get(tp.role, 1.0)
            for tp in touchpoints
        )

        if total_weight == 0:
            # Fall back to equal split
            return self._equal_split(touchpoints)

        # Normalize to sum to 1.0
        splits = {}
        for tp in touchpoints:
            weight = weights_config.get(tp.role, 1.0)
            splits[tp.partner_id] = weight / total_weight

        return splits

    def _activity_weighted(
        self,
        touchpoints: List[PartnerTouchpoint],
        config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Weight by activity level (touchpoint.weight = # of meetings/emails).

        Config:
        {
            "normalize": True  # If true, normalize to sum to 1.0
        }
        """
        total_activity = sum(tp.weight for tp in touchpoints)

        if total_activity == 0:
            # No activity data - fall back to equal split
            return self._equal_split(touchpoints)

        splits = {}
        for tp in touchpoints:
            splits[tp.partner_id] = tp.weight / total_activity

        return splits

    def _time_decay(
        self,
        target: AttributionTarget,
        touchpoints: List[PartnerTouchpoint],
        config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        More recent touchpoints get more credit (exponential decay).

        Config:
        {
            "half_life_days": 30  # Weight halves every 30 days
        }

        Formula: weight = exp(-ln(2) * days_ago / half_life)
        """
        half_life_days = config.get("half_life_days", 30)
        reference_date = target.timestamp  # Usually the close date

        # Calculate decayed weight for each touchpoint
        decayed_weights = {}
        for tp in touchpoints:
            if tp.timestamp is None:
                # Missing timestamp - assign minimum weight
                decayed_weights[tp.partner_id] = 0.01
                continue

            days_ago = (reference_date - tp.timestamp).days
            if days_ago < 0:
                # Touchpoint after close date (shouldn't happen) - assign full weight
                decayed_weights[tp.partner_id] = 1.0
            else:
                # Exponential decay
                decay_factor = math.exp(-math.log(2) * days_ago / half_life_days)
                decayed_weights[tp.partner_id] = decay_factor

        # Normalize to sum to 1.0
        total_weight = sum(decayed_weights.values())
        if total_weight == 0:
            return self._equal_split(touchpoints)

        return {pid: weight / total_weight for pid, weight in decayed_weights.items()}

    def _first_touch(self, touchpoints: List[PartnerTouchpoint]) -> Dict[str, float]:
        """
        100% credit to the earliest touchpoint.
        """
        if not touchpoints:
            return {}

        # Find earliest touchpoint
        earliest = min(touchpoints, key=lambda tp: tp.timestamp or datetime.max)
        return {earliest.partner_id: 1.0}

    def _last_touch(self, touchpoints: List[PartnerTouchpoint]) -> Dict[str, float]:
        """
        100% credit to the most recent touchpoint.
        """
        if not touchpoints:
            return {}

        # Find most recent touchpoint
        latest = max(touchpoints, key=lambda tp: tp.timestamp or datetime.min)
        return {latest.partner_id: 1.0}

    def _linear(self, touchpoints: List[PartnerTouchpoint]) -> Dict[str, float]:
        """
        Equal credit to all touchpoints over time (same as equal_split).
        """
        return self._equal_split(touchpoints)

    def _u_shaped(
        self,
        touchpoints: List[PartnerTouchpoint],
        config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        U-shaped attribution: Heavy weight on first and last touch.

        Config:
        {
            "first_touch_weight": 0.4,
            "last_touch_weight": 0.4,
            "middle_weight": 0.2
        }
        """
        if not touchpoints:
            return {}

        if len(touchpoints) == 1:
            return {touchpoints[0].partner_id: 1.0}

        first_weight = config.get("first_touch_weight", 0.4)
        last_weight = config.get("last_touch_weight", 0.4)
        middle_weight = config.get("middle_weight", 0.2)

        # Sort by timestamp
        sorted_tps = sorted(touchpoints, key=lambda tp: tp.timestamp or datetime.min)

        splits = {}

        # First touchpoint
        splits[sorted_tps[0].partner_id] = first_weight

        # Last touchpoint
        splits[sorted_tps[-1].partner_id] = last_weight

        # Middle touchpoints (if any)
        if len(sorted_tps) > 2:
            middle_tps = sorted_tps[1:-1]
            middle_split = middle_weight / len(middle_tps)
            for tp in middle_tps:
                splits[tp.partner_id] = splits.get(tp.partner_id, 0.0) + middle_split

        return splits

    # ========================================================================
    # Constraint Enforcement
    # ========================================================================

    def _enforce_constraints(
        self,
        splits: Dict[str, float],
        constraint: SplitConstraint
    ) -> Dict[str, float]:
        """
        Enforce split percentage constraints.

        - MUST_SUM_TO_100: Normalize splits to sum to 1.0
        - ALLOW_DOUBLE_COUNTING: No adjustment
        - CAP_AT_100: Cap each partner at 1.0
        - NO_CONSTRAINT: No adjustment
        """

        if constraint == SplitConstraint.MUST_SUM_TO_100:
            total = sum(splits.values())
            if total == 0:
                return splits
            return {pid: pct / total for pid, pct in splits.items()}

        elif constraint == SplitConstraint.CAP_AT_100:
            return {pid: min(pct, 1.0) for pid, pct in splits.items()}

        else:
            # ALLOW_DOUBLE_COUNTING or NO_CONSTRAINT
            return splits

    # ========================================================================
    # Ledger Entry Generation
    # ========================================================================

    def _generate_ledger_entries(
        self,
        target: AttributionTarget,
        splits: Dict[str, float],
        rule: AttributionRule,
        touchpoints: List[PartnerTouchpoint],
        override_by: Optional[str]
    ) -> List[LedgerEntry]:
        """
        Convert splits into LedgerEntry objects with audit trails.
        """
        ledger_entries = []
        calculation_timestamp = datetime.now()

        for partner_id, split_pct in splits.items():
            attributed_value = target.value * split_pct

            # Build audit trail for explainability
            audit_trail = {
                "rule_name": rule.name,
                "model_type": rule.model_type.value,
                "split_constraint": rule.split_constraint.value,
                "target_value": target.value,
                "touchpoint_count": len(touchpoints),
                "partner_touchpoints": [
                    {
                        "partner_id": tp.partner_id,
                        "role": tp.role,
                        "touchpoint_type": tp.touchpoint_type.value,
                        "timestamp": tp.timestamp.isoformat() if tp.timestamp else None,
                        "weight": tp.weight
                    }
                    for tp in touchpoints if tp.partner_id == partner_id
                ],
                "calculation_steps": self._explain_calculation(partner_id, split_pct, rule, touchpoints)
            }

            # Create ledger entry (ID will be assigned by database)
            entry = LedgerEntry(
                id=0,  # Placeholder - database will assign
                target_id=target.id,
                partner_id=partner_id,
                attributed_value=attributed_value,
                split_percentage=split_pct,
                rule_id=rule.id,
                calculation_timestamp=calculation_timestamp,
                override_by=override_by,
                audit_trail=audit_trail
            )

            ledger_entries.append(entry)

        return ledger_entries

    def _explain_calculation(
        self,
        partner_id: str,
        split_pct: float,
        rule: AttributionRule,
        touchpoints: List[PartnerTouchpoint]
    ) -> str:
        """
        Generate human-readable explanation of how this split was calculated.
        """
        partner_tps = [tp for tp in touchpoints if tp.partner_id == partner_id]

        if rule.model_type == AttributionModel.EQUAL_SPLIT:
            return f"Equal split among {len(touchpoints)} partners: {split_pct:.1%} each"

        elif rule.model_type == AttributionModel.ROLE_WEIGHTED:
            roles = [tp.role for tp in partner_tps]
            return f"Role-weighted: {', '.join(roles)} → {split_pct:.1%}"

        elif rule.model_type == AttributionModel.ACTIVITY_WEIGHTED:
            total_weight = sum(tp.weight for tp in partner_tps)
            return f"Activity-weighted: {total_weight} activities → {split_pct:.1%}"

        elif rule.model_type == AttributionModel.TIME_DECAY:
            half_life = rule.config.get("half_life_days", 30)
            return f"Time-decay ({half_life}d half-life) → {split_pct:.1%}"

        elif rule.model_type == AttributionModel.FIRST_TOUCH:
            return f"First touch (earliest partner) → 100%"

        elif rule.model_type == AttributionModel.LAST_TOUCH:
            return f"Last touch (most recent partner) → 100%"

        elif rule.model_type == AttributionModel.U_SHAPED:
            return f"U-shaped attribution → {split_pct:.1%}"

        else:
            return f"{rule.model_type.value} → {split_pct:.1%}"


# ============================================================================
# Utility Functions
# ============================================================================

def select_rule_for_target(
    target: AttributionTarget,
    rules: List[AttributionRule]
) -> Optional[AttributionRule]:
    """
    Select the best rule for a target based on filters and priority.

    Returns:
        The highest-priority active rule that matches the target,
        or None if no rules match.
    """
    # Filter to active rules that match this target
    matching_rules = [
        rule for rule in rules
        if rule.active and rule.matches_target(target)
    ]

    if not matching_rules:
        return None

    # Return highest priority (lowest priority number = highest priority)
    return min(matching_rules, key=lambda r: r.priority)


def calculate_total_attributed(ledger_entries: List[LedgerEntry]) -> float:
    """
    Calculate total attributed value across all ledger entries.
    """
    return sum(entry.attributed_value for entry in ledger_entries)


def get_partner_attribution_summary(
    ledger_entries: List[LedgerEntry]
) -> Dict[str, Dict[str, Any]]:
    """
    Summarize attribution by partner.

    Returns:
        {
            "partner_123": {
                "attributed_value": 50000.0,
                "split_percentage": 0.5,
                "target_count": 3,
                "rules_used": ["Rule A", "Rule B"]
            },
            ...
        }
    """
    summary = {}

    for entry in ledger_entries:
        if entry.partner_id not in summary:
            summary[entry.partner_id] = {
                "attributed_value": 0.0,
                "split_percentage": 0.0,
                "target_count": 0,
                "rules_used": set()
            }

        summary[entry.partner_id]["attributed_value"] += entry.attributed_value
        summary[entry.partner_id]["split_percentage"] += entry.split_percentage
        summary[entry.partner_id]["target_count"] += 1
        summary[entry.partner_id]["rules_used"].add(entry.audit_trail.get("rule_name", "Unknown"))

    # Convert sets to lists for JSON serialization
    for partner_id in summary:
        summary[partner_id]["rules_used"] = list(summary[partner_id]["rules_used"])

    return summary
