"""AI-powered features using OpenAI integration."""

import json
import logging
from typing import Tuple, Optional, Dict, Any, List
from datetime import date

import pandas as pd

from llm import call_llm
from models import PARTNER_ROLES, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


class AIFeatures:
    """AI-powered insights and recommendations."""

    def __init__(self, db):
        self.db = db

    def _normalize_partner_role(self, raw: Optional[str]) -> Optional[str]:
        """Normalize a partner role string to a canonical form."""
        if not raw:
            return None

        raw_lower = str(raw).strip().lower()

        for role in PARTNER_ROLES:
            if raw_lower == role.lower():
                return role

        if "implement" in raw_lower or "si" in raw_lower:
            return "Implementation (SI)"
        if "refer" in raw_lower:
            return "Referral"
        if "isv" in raw_lower or "software" in raw_lower:
            return "ISV"
        if "influenc" in raw_lower:
            return "Influence"

        return None

    def infer_partner_role(
        self,
        account_name: str,
        use_case_name: str,
        partner_name: str,
        context: str
    ) -> Tuple[str, Optional[str]]:
        """
        Use the LLM to select a single partner role. Falls back to heuristics.

        Returns (role, error_message).
        """
        prompt = (
            "Pick one partner role from this list and return JSON with a 'role' key: "
            f"{', '.join(PARTNER_ROLES)}. "
            "Stay concise and avoid explanations.\n"
            f"Account: {account_name}\nUse case: {use_case_name}\nPartner: {partner_name}\nContext: {context or 'n/a'}"
        )

        ok, content, err = call_llm(prompt, system="Return JSON with a single key: role.")
        role = None

        if ok and content:
            try:
                parsed = json.loads(content)
                role = self._normalize_partner_role(parsed.get("role"))
                logger.info(f"LLM inferred role: {role}")
            except Exception as e:
                logger.warning(f"Failed to parse LLM response: {e}")
                role = None

        # Fallback to heuristics
        if role is None:
            combined = " ".join([account_name or "", use_case_name or "", partner_name or "", context or ""]).lower()
            role = self._normalize_partner_role(combined)
            logger.info(f"Heuristic inferred role: {role}")

        if role is None:
            role = "Influence"
            logger.info("Defaulting to Influence role")

        return role, err

    def _heuristic_rule_from_text(self, text: str) -> Dict[str, Any]:
        """Create a rule from text using simple heuristics."""
        lower = text.lower()
        name = text.strip()[:60] or "Custom rule"
        action = "allow"

        if "only" in lower and "not" in lower or "block" in lower or "deny" in lower:
            action = "deny"

        when = {}
        stages = ["discovery", "evaluation", "commit", "live"]
        for s in stages:
            if s in lower:
                when["stage"] = s.capitalize()
                break

        numbers = [int(tok) for tok in lower.replace(">", " ").replace("$", " ").split() if tok.isdigit()]
        if numbers:
            val = numbers[0]
            if ">" in lower or "over" in lower or "above" in lower:
                when["min_estimated_value"] = val
            elif "<" in lower or "under" in lower or "below" in lower:
                when["max_estimated_value"] = val

        if "si" in lower or "implementation" in lower:
            when["partner_role"] = "Implementation (SI)"

        logger.info(f"Heuristic rule created: {name} - {action} - {when}")
        return {"name": name, "action": action, "when": when}

    def convert_nl_to_rule(self, text: str) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Convert natural language to a rule using LLM.

        Falls back to heuristics if LLM is not available.
        Returns (rule_dict, error_message).
        """
        base_prompt = self.db.get_setting("prompt_rule_conversion", DEFAULT_SETTINGS["prompt_rule_conversion"])
        prompt = f"{base_prompt}\nDescription:\n{text}"

        ok, content, err = call_llm(prompt, system="Return JSON only.")
        rule = None

        if ok and content:
            try:
                rule = json.loads(content)
                logger.info(f"LLM generated rule: {rule}")
            except Exception as e:
                logger.warning(f"Failed to parse LLM rule response: {e}")
                rule = None

        if rule is None:
            rule = self._heuristic_rule_from_text(text)
            logger.info("Using heuristic rule fallback")

        return rule, err

    def generate_relationship_summary(self, account_id: str) -> Tuple[str, Optional[str]]:
        """
        Generate an AI summary of account relationships.

        Returns (summary_text, error_message).
        """
        acct = self.db.read_sql("SELECT account_name FROM accounts WHERE account_id = ?;", (account_id,))
        acct_name = acct.loc[0, "account_name"] if not acct.empty else account_id

        use_cases = self.db.read_sql("SELECT use_case_name, stage FROM use_cases WHERE account_id = ?;", (account_id,))
        activities = self.db.read_sql(
            "SELECT activity_type, activity_date, notes FROM activities WHERE account_id = ? ORDER BY activity_date DESC LIMIT 5;",
            (account_id,)
        )
        rev = self.db.read_sql(
            "SELECT SUM(attributed_amount) AS total_attr FROM attribution_events WHERE account_id = ? AND revenue_date >= date('now','-30 day');",
            (account_id,)
        )

        total_attr = float(rev['total_attr'].iloc[0] or 0)
        base_summary = f"{acct_name}: {len(use_cases)} use cases, recent attributed revenue {total_attr:,.0f} in last 30d."

        if activities.empty:
            activity_txt = "No recent activities."
        else:
            rows = [f"{row['activity_date']}: {row['activity_type']} ({row['notes']})" for _, row in activities.iterrows()]
            activity_txt = "; ".join(rows)

        base_prompt = self.db.get_setting("prompt_relationship_summary", DEFAULT_SETTINGS["prompt_relationship_summary"])
        prompt = f"{base_prompt}\nAccount: {base_summary}\nActivities: {activity_txt}"

        ok, content, err = call_llm(prompt, system="Concise summary.")

        if ok and content:
            logger.info(f"Generated relationship summary for {account_id}")
            return content, None

        # Fallback deterministic
        fallback = f"{base_summary} Activities: {activity_txt}"
        logger.info(f"Using fallback summary for {account_id}")
        return fallback, err or "LLM not available"

    def generate_ai_recommendations(self, account_id: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Generate AI recommendations for partner attributions.

        Returns (recommendations_list, error_message).
        """
        acct_name = self.db.read_sql("SELECT account_name FROM accounts WHERE account_id = ?;", (account_id,))
        acct_name = acct_name.loc[0, "account_name"] if not acct_name.empty else account_id

        base_prompt = self.db.get_setting("prompt_ai_recommendations", DEFAULT_SETTINGS["prompt_ai_recommendations"])
        prompt = (
            f"{base_prompt}\nAccount context: {acct_name} ({account_id}). "
            "Use known partners if present; otherwise suggest from existing partners."
        )

        ok, content, err = call_llm(prompt, system="Return JSON only.")
        recs = None

        if ok and content:
            try:
                recs = json.loads(content)
                logger.info(f"LLM generated {len(recs)} recommendations")
            except Exception as e:
                logger.warning(f"Failed to parse LLM recommendations: {e}")
                recs = None

        if recs is None or not isinstance(recs, list):
            # Fallback: pick top existing partner or first partner
            ledger = self.db.read_sql("""
              SELECT actor_id, SUM(attributed_amount) AS amt
              FROM attribution_events
              WHERE account_id = ?
              GROUP BY actor_id
              ORDER BY amt DESC
              LIMIT 1;
            """, (account_id,))

            partners = self.db.read_sql("SELECT partner_id FROM partners ORDER BY partner_name;")
            target_partner = ledger["actor_id"].iloc[0] if not ledger.empty else (partners["partner_id"].iloc[0] if not partners.empty else None)

            if target_partner:
                recs = [{
                    "partner_id": target_partner,
                    "recommended_role": "Influence",
                    "recommended_split_percent": 20,
                    "confidence": 0.5,
                    "reasons": "Heuristic fallback without LLM."
                }]
                logger.info(f"Using heuristic recommendation: {target_partner}")
            else:
                recs = []
                logger.warning("No partners available for recommendations")

        return recs, err

    def apply_recommendations(self, account_id: str, recs: List[Dict[str, Any]], attribution_engine) -> Dict[str, int]:
        """
        Apply AI recommendations to an account.

        Returns statistics about the application.
        """
        today_str = date.today().isoformat()
        stats = {"applied": 0, "blocked_cap": 0, "skipped_manual": 0, "invalid": 0, "missing_use_case": 0}

        use_cases = self.db.read_sql("SELECT use_case_id FROM use_cases WHERE account_id = ?;", (account_id,))
        uc_for_links = use_cases["use_case_id"].iloc[0] if not use_cases.empty else None

        for rec in recs:
            pid = rec.get("partner_id")
            role = rec.get("recommended_role", "Influence")
            split_pct = rec.get("recommended_split_percent", 0)

            if not pid or split_pct is None:
                stats["invalid"] += 1
                logger.warning(f"Invalid recommendation: {rec}")
                continue

            split = float(split_pct) / 100.0

            # Check if manual entry exists
            existing = self.db.read_sql(
                "SELECT source, first_seen FROM account_partners WHERE account_id = ? AND partner_id = ?;",
                (account_id, pid)
            )
            if not existing.empty and existing.loc[0, "source"] == "manual":
                stats["skipped_manual"] += 1
                logger.info(f"Skipping recommendation for manual entry: {pid}")
                continue

            # Check split cap
            if attribution_engine.should_enforce_split_cap():
                exceeds, _ = attribution_engine.will_exceed_split_cap(account_id, pid, split)
                if exceeds:
                    stats["blocked_cap"] += 1
                    logger.warning(f"Recommendation blocked by split cap: {pid}")
                    continue

            first_seen = existing.loc[0, "first_seen"] if not existing.empty else today_str

            # Apply recommendation
            self.db.run_sql("""
                INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source)
                VALUES (?, ?, ?, ?, ?, 'ai')
                ON CONFLICT(account_id, partner_id)
                DO UPDATE SET split_percent=excluded.split_percent, last_seen=excluded.last_seen, source=excluded.source;
            """, (account_id, pid, split, first_seen, today_str))

            # Link to use case if available
            if uc_for_links:
                self.db.run_sql("""
                INSERT INTO use_case_partners(use_case_id, partner_id, partner_role, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(use_case_id, partner_id) DO UPDATE SET partner_role=excluded.partner_role;
                """, (uc_for_links, pid, role, today_str))
            else:
                stats["missing_use_case"] += 1

            # Log audit event
            self.db.log_audit_event(
                event_type="ai_recommendation_applied",
                account_id=account_id,
                partner_id=pid,
                changed_field="split_percent",
                new_value=str(split),
                source="ai",
                metadata={"role": role, "confidence": rec.get("confidence")}
            )

            stats["applied"] += 1
            logger.info(f"Applied AI recommendation: {pid} @ {split:.2%}")

        logger.info(f"Recommendations applied: {stats}")
        return stats
