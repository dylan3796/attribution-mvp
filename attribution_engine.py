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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from models import (
    AttributionTarget,
    PartnerTouchpoint,
    AttributionRule,
    LedgerEntry,
    AttributionModel,
    SplitConstraint,
    DataSource,
    DataSourceConfig,
    MeasurementWorkflow,
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

    # ========================================================================
    # Multi-Source Workflow Calculation (Phase 2)
    # ========================================================================

    def calculate_with_workflow(
        self,
        target: AttributionTarget,
        touchpoints: List[PartnerTouchpoint],
        rule: AttributionRule,
        workflow: MeasurementWorkflow,
        override_by: Optional[str] = None
    ) -> List[LedgerEntry]:
        """
        Calculate attribution using a measurement workflow.

        This is the NEW entry point for flexible multi-source attribution.
        It allows companies to configure exactly how they want to measure
        partner impact by:
        1. Grouping touchpoints by data source
        2. Applying workflow priority/conflict resolution logic
        3. Selecting the right touchpoints based on workflow config
        4. Calculating attribution using existing models
        5. Generating ledger with source attribution trail

        Args:
            target: What's being attributed (opportunity, consumption event, etc.)
            touchpoints: ALL touchpoints from ALL sources
            rule: Attribution calculation rule (role-weighted, time-decay, etc.)
            workflow: Measurement workflow configuration
            override_by: User who manually triggered this (if applicable)

        Returns:
            List of LedgerEntry objects (one per partner getting credit)

        Example workflows:
        - Priority: Use deal reg if exists, else touchpoints
        - Merge: 80% deal reg + 20% influence touchpoints
        - Manual: Flag for human review when sources conflict
        """

        # Step 1: Group touchpoints by data source
        touchpoints_by_source = self._group_by_source(touchpoints)

        # Step 2: Apply workflow logic to select which touchpoints to use
        selected_touchpoints = self._apply_workflow_logic(
            touchpoints_by_source,
            workflow,
            target
        )

        if not selected_touchpoints:
            # No data from primary sources - try fallback strategy
            selected_touchpoints = self._apply_fallback_strategy(
                touchpoints_by_source,
                workflow,
                target
            )

        if not selected_touchpoints:
            # No partner data available from any source
            return []

        # Step 3: Use existing calculate() method for attribution calculation
        # This reuses all the existing model logic (role-weighted, time-decay, etc.)
        return self.calculate(target, selected_touchpoints, rule, override_by)

    def _group_by_source(
        self,
        touchpoints: List[PartnerTouchpoint]
    ) -> Dict[DataSource, List[PartnerTouchpoint]]:
        """
        Group touchpoints by their data source.

        Returns:
            {
                DataSource.DEAL_REGISTRATION: [tp1, tp2],
                DataSource.TOUCHPOINT_TRACKING: [tp3, tp4, tp5],
                DataSource.MARKETPLACE_TRANSACTIONS: [tp6]
            }
        """
        grouped = {}
        for tp in touchpoints:
            source = tp.source
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(tp)

        return grouped

    def _apply_workflow_logic(
        self,
        touchpoints_by_source: Dict[DataSource, List[PartnerTouchpoint]],
        workflow: MeasurementWorkflow,
        target: AttributionTarget
    ) -> List[PartnerTouchpoint]:
        """
        Apply workflow configuration to select touchpoints.

        Workflow conflict resolution strategies:
        - "priority": Use highest priority source that has data
        - "merge": Weighted combination of multiple sources
        - "manual_review": Return empty (flag for human decision)
        """

        conflict_resolution = workflow.conflict_resolution

        if conflict_resolution == "priority":
            return self._priority_selection(touchpoints_by_source, workflow)

        elif conflict_resolution == "merge":
            return self._merge_sources(touchpoints_by_source, workflow)

        elif conflict_resolution == "manual_review":
            # Flag for manual review - return empty so caller can handle
            return []

        else:
            # Default to priority if unknown strategy
            return self._priority_selection(touchpoints_by_source, workflow)

    def _priority_selection(
        self,
        touchpoints_by_source: Dict[DataSource, List[PartnerTouchpoint]],
        workflow: MeasurementWorkflow
    ) -> List[PartnerTouchpoint]:
        """
        Select touchpoints from highest priority source that has data.

        Example workflow:
        - Priority 1: Deal Registration (if exists, use this)
        - Priority 2: CRM Partner Field (else use this)
        - Priority 3: Touchpoint Tracking (fallback to this)

        Returns touchpoints from the first enabled source (by priority) that has data.
        """

        # Sort data sources by priority (lower number = higher priority)
        sorted_sources = sorted(
            workflow.data_sources,
            key=lambda ds: ds.priority
        )

        for source_config in sorted_sources:
            # Skip disabled sources
            if not source_config.enabled:
                continue

            # Check if we have data from this source
            if source_config.source_type in touchpoints_by_source:
                touchpoints = touchpoints_by_source[source_config.source_type]

                # Apply source-specific filters
                filtered = self._apply_source_filters(touchpoints, source_config)

                if filtered:
                    # Found data from this source - use it!
                    return filtered

        # No data from any configured source
        return []

    def _merge_sources(
        self,
        touchpoints_by_source: Dict[DataSource, List[PartnerTouchpoint]],
        workflow: MeasurementWorkflow
    ) -> List[PartnerTouchpoint]:
        """
        Combine touchpoints from multiple sources with weighting.

        Example: "80% to deal reg partner, 20% to influence touchpoints"
        - Deal reg touchpoint gets weight multiplier of 0.8
        - Influence touchpoints get weight multiplier of 0.2

        The attribution engine will then use these weighted touchpoints
        to calculate splits (e.g., via activity-weighted model).
        """

        merged_touchpoints = []

        for source_config in workflow.data_sources:
            # Skip disabled sources
            if not source_config.enabled:
                continue

            # Check if we have data from this source
            if source_config.source_type not in touchpoints_by_source:
                continue

            touchpoints = touchpoints_by_source[source_config.source_type]

            # Apply source-specific filters
            filtered = self._apply_source_filters(touchpoints, source_config)

            # Apply attribution weight from config
            weight_multiplier = source_config.config.get("attribution_weight", 1.0)

            for tp in filtered:
                # Create weighted copy of touchpoint
                weighted_tp = PartnerTouchpoint(
                    id=tp.id,
                    partner_id=tp.partner_id,
                    target_id=tp.target_id,
                    touchpoint_type=tp.touchpoint_type,
                    role=tp.role,
                    weight=tp.weight * weight_multiplier,  # Apply weight multiplier
                    timestamp=tp.timestamp,
                    source=tp.source,
                    source_id=tp.source_id,
                    source_confidence=tp.source_confidence,
                    deal_reg_status=tp.deal_reg_status,
                    deal_reg_submitted_date=tp.deal_reg_submitted_date,
                    deal_reg_approved_date=tp.deal_reg_approved_date,
                    requires_approval=tp.requires_approval,
                    approved_by=tp.approved_by,
                    approval_timestamp=tp.approval_timestamp,
                    metadata=tp.metadata,
                    created_at=tp.created_at
                )
                merged_touchpoints.append(weighted_tp)

        return merged_touchpoints

    def _apply_fallback_strategy(
        self,
        touchpoints_by_source: Dict[DataSource, List[PartnerTouchpoint]],
        workflow: MeasurementWorkflow,
        target: AttributionTarget
    ) -> List[PartnerTouchpoint]:
        """
        Apply fallback strategy when primary workflow has no data.

        Strategies:
        - "next_priority": Try lower priority sources (already handled by priority_selection)
        - "equal_split": Use all available touchpoints with equal weight
        - "manual": Return empty (flag for human review)
        """

        fallback_strategy = workflow.fallback_strategy

        if fallback_strategy == "next_priority":
            # Priority selection already handles this - no additional fallback needed
            return []

        elif fallback_strategy == "equal_split":
            # Combine all touchpoints from all sources with equal weight
            all_touchpoints = []
            for touchpoints in touchpoints_by_source.values():
                all_touchpoints.extend(touchpoints)
            return all_touchpoints

        elif fallback_strategy == "manual":
            # Flag for manual review
            return []

        else:
            # Default: return empty
            return []

    def _apply_source_filters(
        self,
        touchpoints: List[PartnerTouchpoint],
        source_config: DataSourceConfig
    ) -> List[PartnerTouchpoint]:
        """
        Apply source-specific filters from DataSourceConfig.

        Example filters:
        - Deal Reg: {"require_approval": True, "expiry_days": 90}
          → Only approved deal regs from last 90 days
        - CRM Field: {"field_name": "Partner__c"}
          → Filter by specific CRM field
        - Touchpoints: {"min_activity_count": 3}
          → Only partners with 3+ activities
        """
        filtered = touchpoints

        config = source_config.config

        # Filter by approval requirement
        if config.get("require_approval", False):
            filtered = [
                tp for tp in filtered
                if tp.approved_by is not None or not tp.requires_approval
            ]

        # Filter by deal reg status
        if "required_deal_reg_status" in config:
            required_status = config["required_deal_reg_status"]
            filtered = [
                tp for tp in filtered
                if tp.deal_reg_status == required_status
            ]

        # Filter by expiry (for deal registrations)
        if "expiry_days" in config:
            expiry_days = config["expiry_days"]
            cutoff_date = datetime.now() - timedelta(days=expiry_days)
            filtered = [
                tp for tp in filtered
                if tp.timestamp and tp.timestamp >= cutoff_date
            ]

        # Filter by minimum activity count
        if "min_activity_count" in config:
            min_count = config["min_activity_count"]
            filtered = [tp for tp in filtered if tp.weight >= min_count]

        # Validation requirement
        if source_config.requires_validation:
            filtered = [
                tp for tp in filtered
                if tp.approved_by is not None
            ]

        return filtered

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
