"""Rule engine for evaluating partner attribution rules."""

import json
import hashlib
import logging
from typing import Tuple, Optional, Dict, Any, List

from models import RuleContext, RuleEvaluationResult, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


class RuleEngine:
    """Rule engine for evaluating business rules."""

    def __init__(self, db):
        self.db = db

    def load_rules(self, key: str) -> List[Dict[str, Any]]:
        """Load rules from settings."""
        try:
            raw = self.db.get_setting(key, DEFAULT_SETTINGS.get(key, "[]"))
            rules = json.loads(raw)
            logger.debug(f"Loaded {len(rules)} rules from {key}")
            return rules
        except Exception as e:
            logger.error(f"Error loading rules from {key}: {e}")
            return []

    def save_rules(self, key: str, rules: List[Dict[str, Any]]) -> None:
        """Save rules to settings."""
        try:
            rules_json = json.dumps(rules, indent=2)
            self.db.set_setting(key, rules_json)
            logger.info(f"Saved {len(rules)} rules to {key}")
        except Exception as e:
            logger.error(f"Error saving rules to {key}: {e}")
            raise

    def _matches_value(self, field_value: Any, rule_value: Any) -> bool:
        """Check if a field value matches a rule value."""
        if isinstance(rule_value, list):
            return field_value in rule_value
        return field_value == rule_value

    def rule_matches(self, rule_when: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
        """Check if a rule matches the given context."""
        if not rule_when:
            return True

        if "partner_role" in rule_when and not self._matches_value(ctx.get("partner_role"), rule_when["partner_role"]):
            return False

        if "stage" in rule_when and not self._matches_value(ctx.get("stage"), rule_when["stage"]):
            return False

        if "min_estimated_value" in rule_when and ctx.get("estimated_value") is not None:
            if ctx["estimated_value"] < float(rule_when["min_estimated_value"]):
                return False

        if "max_estimated_value" in rule_when and ctx.get("estimated_value") is not None:
            if ctx["estimated_value"] > float(rule_when["max_estimated_value"]):
                return False

        return True

    def evaluate_rules(
        self,
        ctx: Dict[str, Any],
        key: str
    ) -> RuleEvaluationResult:
        """
        Evaluate rules against a context.

        Returns RuleEvaluationResult with details about the evaluation.
        If rules exist but none match, we block to avoid silent bypass.
        """
        rules = self.load_rules(key)
        matched = False

        for idx, rule in enumerate(rules):
            when = rule.get("when", {})
            if self.rule_matches(when, ctx):
                matched = True
                action = rule.get("action", "allow")
                name = rule.get("name", "Unnamed rule")

                if action == "deny":
                    logger.info(f"Rule {name} blocked: {ctx}")
                    return RuleEvaluationResult(
                        allowed=False,
                        message=f"Blocked by rule: {name}",
                        matched_any_rule=matched,
                        matched_rule_index=idx,
                        rule_name=name
                    )

                logger.info(f"Rule {name} allowed: {ctx}")
                return RuleEvaluationResult(
                    allowed=True,
                    message=f"Allowed by rule: {name}",
                    matched_any_rule=matched,
                    matched_rule_index=idx,
                    rule_name=name
                )

        if rules:
            logger.warning(f"No matching rule for context: {ctx}")
            return RuleEvaluationResult(
                allowed=False,
                message="No matching rule; blocked by default. Add an 'allow' rule for these conditions.",
                matched_any_rule=matched,
                matched_rule_index=None,
                rule_name=None
            )

        logger.debug(f"No rules defined for {key}, allowing by default")
        return RuleEvaluationResult(
            allowed=True,
            message="No rules defined; allowed by default.",
            matched_any_rule=matched,
            matched_rule_index=None,
            rule_name=None
        )

    def get_rule_version(self, key: str) -> str:
        """Get a version hash for the current rules."""
        raw = self.db.get_setting(key, DEFAULT_SETTINGS.get(key, "[]"))
        digest = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"{key}:{digest}"

    def validate_rule_obj(self, rule: Dict[str, Any]) -> bool:
        """Validate a rule object structure."""
        if not isinstance(rule, dict):
            return False
        if "name" not in rule or "action" not in rule or "when" not in rule:
            return False
        if rule["action"] not in ["allow", "deny"]:
            return False
        if not isinstance(rule["when"], dict):
            return False
        return True

    def generate_rule_suggestion(self) -> Dict[str, Any]:
        """
        Generate a rule suggestion based on current data distribution.
        This is a lightweight, local heuristic that mimics AI assistance.
        """
        import random
        from models import PARTNER_ROLES

        use_cases = self.db.read_sql("SELECT stage, estimated_value FROM use_cases;")
        common_stage = "Commit"

        if not use_cases.empty and "stage" in use_cases:
            mode_stage = use_cases["stage"].mode(dropna=True)
            if not mode_stage.empty:
                common_stage = mode_stage.iloc[0]

        if use_cases.empty or "estimated_value" not in use_cases or use_cases["estimated_value"].dropna().empty:
            typical_val = 5000
        else:
            typical_val = float(use_cases["estimated_value"].dropna().median())

        # Nudge threshold above the typical value to focus on higher-risk items
        threshold = max(2000, min(100000, int(round((typical_val * 1.2) / 1000.0) * 1000)))
        role = random.choice(PARTNER_ROLES)

        suggestion = {
            "name": f"AI suggestion: Gate {role} in {common_stage}",
            "action": "deny",
            "when": {
                "partner_role": role,
                "stage": common_stage,
                "min_estimated_value": threshold
            }
        }

        logger.info(f"Generated rule suggestion: {suggestion}")
        return suggestion
