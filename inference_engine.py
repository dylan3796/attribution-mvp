"""
Touchpoint Inference Engine
============================

Maps indirect partner signals to opportunities:
- Activities (Tasks, Events) → Opportunities
- Campaign Members → Opportunities
- Contact Roles → Opportunities
- Partner self-reported activities → Opportunities

Includes confidence scoring and decay logic.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re

from models import (
    PartnerTouchpoint, AttributionTarget,
    TouchpointType, DataSource
)


# ============================================================================
# Inference Configuration
# ============================================================================

@dataclass
class InferenceConfig:
    """Configuration for touchpoint → opportunity inference."""

    # Time decay
    time_decay_enabled: bool = True
    time_decay_window_days: int = 90  # Activities older than 90 days get lower weight
    time_decay_rate: float = 0.5  # Weight multiplier for old activities

    # Proximity bonus
    proximity_bonus_enabled: bool = True
    proximity_bonus_days: int = 14  # Activities within 14 days of close get bonus
    proximity_bonus_multiplier: float = 1.5

    # Contact → Account mapping
    contact_account_mapping_enabled: bool = True

    # Activity type weights
    activity_type_weights: Dict[str, float] = None

    # Minimum confidence threshold
    min_confidence: float = 0.3

    def __post_init__(self):
        if self.activity_type_weights is None:
            self.activity_type_weights = {
                "Meeting": 1.0,
                "Call": 0.7,
                "Email": 0.5,
                "Demo": 1.5,
                "Technical Workshop": 2.0,
                "Referral": 2.5,
                "Introduction": 1.2
            }


# ============================================================================
# Inference Engine
# ============================================================================

class TouchpointInferenceEngine:
    """
    Infers which opportunities a touchpoint should be attributed to.

    Process:
    1. Find candidate opportunities (account match, time proximity)
    2. Calculate confidence score for each candidate
    3. Apply inference rules (time decay, proximity bonus)
    4. Return touchpoint → opportunity mappings
    """

    def __init__(self, config: Optional[InferenceConfig] = None):
        self.config = config or InferenceConfig()

    def infer_opportunity_for_touchpoint(
        self,
        touchpoint: PartnerTouchpoint,
        opportunities: List[AttributionTarget],
        contact_to_account_map: Optional[Dict[str, str]] = None
    ) -> List[Tuple[str, float]]:
        """
        Infer which opportunities this touchpoint relates to.

        Args:
            touchpoint: Partner touchpoint to map
            opportunities: All available opportunities
            contact_to_account_map: Contact ID → Account ID mapping

        Returns:
            List of (opportunity_external_id, confidence_score) tuples
        """
        # Step 1: Filter candidate opportunities
        candidates = self._get_candidate_opportunities(
            touchpoint,
            opportunities,
            contact_to_account_map
        )

        if not candidates:
            return []

        # Step 2: Score each candidate
        scored_candidates = []
        for opp in candidates:
            confidence = self._calculate_confidence(touchpoint, opp)

            if confidence >= self.config.min_confidence:
                scored_candidates.append((opp.external_id, confidence))

        # Step 3: Sort by confidence
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return scored_candidates

    def _get_candidate_opportunities(
        self,
        touchpoint: PartnerTouchpoint,
        opportunities: List[AttributionTarget],
        contact_to_account_map: Optional[Dict[str, str]]
    ) -> List[AttributionTarget]:
        """Find opportunities that could be related to this touchpoint."""

        candidates = []

        # Get account ID from touchpoint metadata or contact mapping
        account_id = touchpoint.metadata.get("account_id")

        if not account_id and contact_to_account_map:
            # Try to map contact → account
            contact_id = touchpoint.partner_id  # Assuming partner_id is contact for now
            account_id = contact_to_account_map.get(contact_id)

        if not account_id:
            # No account match possible - return all opportunities within time window
            time_window_start = touchpoint.timestamp - timedelta(days=self.config.time_decay_window_days)
            time_window_end = touchpoint.timestamp + timedelta(days=30)  # Allow future attribution

            candidates = [
                opp for opp in opportunities
                if time_window_start <= opp.timestamp <= time_window_end
            ]
        else:
            # Filter by account match
            candidates = [
                opp for opp in opportunities
                if opp.metadata.get("account_id") == account_id
            ]

        return candidates

    def _calculate_confidence(
        self,
        touchpoint: PartnerTouchpoint,
        opportunity: AttributionTarget
    ) -> float:
        """
        Calculate confidence score (0-1) that touchpoint influenced opportunity.

        Factors:
        - Time proximity to close date
        - Activity type
        - Touchpoint source (deal reg = 1.0, activity = 0.6)
        - Account match (explicit match = +0.2 bonus)
        """
        base_confidence = touchpoint.source_confidence or 0.6

        # Time proximity factor
        time_factor = self._calculate_time_factor(touchpoint, opportunity)

        # Activity type factor
        activity_factor = self._calculate_activity_factor(touchpoint)

        # Account match bonus
        account_match_bonus = 0.2 if self._has_account_match(touchpoint, opportunity) else 0.0

        # Combined confidence (cap at 1.0)
        confidence = min(1.0, base_confidence * time_factor * activity_factor + account_match_bonus)

        return confidence

    def _calculate_time_factor(
        self,
        touchpoint: PartnerTouchpoint,
        opportunity: AttributionTarget
    ) -> float:
        """Calculate time-based weight factor."""

        days_before_close = (opportunity.timestamp - touchpoint.timestamp).days

        # Future touchpoints (after close) get very low weight
        if days_before_close < 0:
            return 0.1

        # Recent touchpoints (within proximity window) get bonus
        if self.config.proximity_bonus_enabled and days_before_close <= self.config.proximity_bonus_days:
            return self.config.proximity_bonus_multiplier

        # Old touchpoints (beyond decay window) get penalty
        if self.config.time_decay_enabled and days_before_close > self.config.time_decay_window_days:
            return self.config.time_decay_rate

        # Normal range
        return 1.0

    def _calculate_activity_factor(self, touchpoint: PartnerTouchpoint) -> float:
        """Calculate activity type weight factor."""

        activity_type = touchpoint.metadata.get("activity_type", "Unknown")

        # Get weight from config
        return self.config.activity_type_weights.get(activity_type, 0.8)

    def _has_account_match(
        self,
        touchpoint: PartnerTouchpoint,
        opportunity: AttributionTarget
    ) -> bool:
        """Check if touchpoint and opportunity share same account."""

        tp_account = touchpoint.metadata.get("account_id")
        opp_account = opportunity.metadata.get("account_id")

        return tp_account is not None and tp_account == opp_account

    # ========================================================================
    # Batch Inference
    # ========================================================================

    def infer_all_touchpoints(
        self,
        touchpoints: List[PartnerTouchpoint],
        opportunities: List[AttributionTarget],
        contact_to_account_map: Optional[Dict[str, str]] = None
    ) -> Dict[int, List[Tuple[str, float]]]:
        """
        Infer opportunities for all touchpoints.

        Returns:
            Dict mapping touchpoint_id → [(opp_external_id, confidence), ...]
        """
        results = {}

        for touchpoint in touchpoints:
            # Skip if already explicitly linked
            if touchpoint.target_id != 0:
                continue

            # Skip if source is already definitive (deal reg, CRM field)
            if touchpoint.source in [DataSource.DEAL_REGISTRATION, DataSource.CRM_OPPORTUNITY_FIELD]:
                continue

            # Infer opportunities
            inferred = self.infer_opportunity_for_touchpoint(
                touchpoint,
                opportunities,
                contact_to_account_map
            )

            if inferred:
                results[touchpoint.id] = inferred

        return results


# ============================================================================
# Account Name Matching (Fuzzy)
# ============================================================================

class AccountMatcher:
    """Fuzzy matching for account names (for self-reported activities)."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize account name for matching."""
        # Remove Inc, LLC, Ltd, etc.
        name = re.sub(r'\b(Inc|LLC|Ltd|Corporation|Corp|Company|Co)\b', '', name, flags=re.IGNORECASE)

        # Remove special characters
        name = re.sub(r'[^a-zA-Z0-9\s]', '', name)

        # Lowercase and strip
        return name.lower().strip()

    @staticmethod
    def find_matching_account(
        input_name: str,
        known_accounts: List[Dict[str, str]]
    ) -> Optional[Tuple[str, float]]:
        """
        Find best matching account from known accounts.

        Args:
            input_name: Account name from partner (e.g., "Acme Corp")
            known_accounts: List of {id, name} dicts from CRM

        Returns:
            (account_id, confidence) or None
        """
        normalized_input = AccountMatcher.normalize_name(input_name)

        best_match = None
        best_score = 0.0

        for account in known_accounts:
            normalized_account = AccountMatcher.normalize_name(account["name"])

            # Exact match
            if normalized_input == normalized_account:
                return (account["id"], 1.0)

            # Substring match
            if normalized_input in normalized_account or normalized_account in normalized_input:
                score = 0.8
                if score > best_score:
                    best_score = score
                    best_match = account["id"]

            # Word overlap
            input_words = set(normalized_input.split())
            account_words = set(normalized_account.split())
            overlap = len(input_words & account_words)

            if overlap > 0:
                score = overlap / max(len(input_words), len(account_words))
                if score > best_score:
                    best_score = score
                    best_match = account["id"]

        # Only return if confidence is reasonable
        if best_score >= 0.6:
            return (best_match, best_score)

        return None


# ============================================================================
# Inference Report
# ============================================================================

def generate_inference_report(
    touchpoints: List[PartnerTouchpoint],
    inference_results: Dict[int, List[Tuple[str, float]]],
    opportunities: List[AttributionTarget]
) -> str:
    """Generate human-readable inference report."""

    report_lines = [
        "=" * 80,
        "TOUCHPOINT INFERENCE REPORT",
        "=" * 80,
        ""
    ]

    # Summary
    total_touchpoints = len(touchpoints)
    inferred_touchpoints = len(inference_results)
    total_mappings = sum(len(mappings) for mappings in inference_results.values())

    report_lines.extend([
        f"Total Touchpoints: {total_touchpoints}",
        f"Touchpoints with Inferences: {inferred_touchpoints}",
        f"Total Opportunity Mappings: {total_mappings}",
        f"Avg Mappings per Touchpoint: {total_mappings / inferred_touchpoints if inferred_touchpoints > 0 else 0:.1f}",
        "",
        "=" * 80,
        "DETAILED MAPPINGS",
        "=" * 80,
        ""
    ])

    # Detailed mappings
    for tp_id, mappings in inference_results.items():
        touchpoint = next((tp for tp in touchpoints if tp.id == tp_id), None)
        if not touchpoint:
            continue

        report_lines.extend([
            f"Touchpoint #{tp_id}:",
            f"  Type: {touchpoint.touchpoint_type.value}",
            f"  Partner: {touchpoint.partner_id}",
            f"  Date: {touchpoint.timestamp.strftime('%Y-%m-%d')}",
            f"  Source: {touchpoint.source.value}",
            "",
            f"  Mapped to {len(mappings)} opportunity(ies):"
        ])

        for opp_id, confidence in mappings:
            opp = next((o for o in opportunities if o.external_id == opp_id), None)
            if opp:
                report_lines.append(
                    f"    - {opp.name or opp_id} (${opp.value:,.0f}) - Confidence: {confidence:.1%}"
                )

        report_lines.append("")

    return "\n".join(report_lines)
