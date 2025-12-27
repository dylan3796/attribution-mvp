"""Attribution calculation and management logic."""

import json
import uuid
import logging
from datetime import date, datetime, timedelta
from typing import Tuple, Optional, Dict, Any, List

import pandas as pd

from models import (
    AttributionResult,
    ApplySummary,
    LedgerResult,
    SimulationResult
)

logger = logging.getLogger(__name__)


class AttributionEngine:
    """Attribution calculation and management."""

    def __init__(self, db, rule_engine):
        self.db = db
        self.rule_engine = rule_engine

    def should_enforce_split_cap(self) -> bool:
        """Check if split cap enforcement is enabled."""
        return self.db.get_setting_bool("enforce_split_cap", default=True)

    def will_exceed_split_cap(
        self,
        account_id: str,
        partner_id: str,
        new_split: float
    ) -> Tuple[bool, float]:
        """
        Check if adding a split would exceed 100% cap.

        Returns (exceeds, total_with_new). Excludes current partner's existing
        split when replacing.
        """
        current = self.db.read_sql("""
            SELECT partner_id, split_percent
            FROM account_partners
            WHERE account_id = ?;
        """, (account_id,))

        total_other = current[current["partner_id"] != partner_id]["split_percent"].sum()
        total_with_new = total_other + float(new_split)
        exceeds = total_with_new > 1.00001  # small tolerance

        if exceeds:
            logger.warning(f"Split cap exceeded for {account_id}/{partner_id}: {total_with_new:.2%}")

        return exceeds, total_with_new

    def compute_si_auto_split(
        self,
        use_case_value: float,
        account_live_total: float,
        account_all_total: float,
        mode: str
    ) -> Tuple[Optional[float], str]:
        """
        Compute Implementation (SI) auto split percentage.

        Returns (split, explanation). split None means auto not applicable.
        """
        mode = mode or "live_share"

        if mode == "manual_only":
            return None, "Manual-only mode."

        if mode == "fixed_percent":
            fixed = float(self.db.get_setting("si_fixed_percent", "0")) / 100.0
            return min(max(fixed, 0.0), 1.0), "Fixed percent from settings."

        # live_share default
        base_total = account_live_total if account_live_total > 0 else account_all_total
        if base_total <= 0:
            return None, "No totals available to calculate share."

        split = min(use_case_value / base_total, 1.0) if base_total > 0 else None
        logger.debug(f"SI auto split: {split:.2%} ({use_case_value}/{base_total})")
        return split, "Use case value divided by account total."

    def upsert_account_partner_from_use_case_partner(
        self,
        use_case_id: str,
        partner_id: str,
        partner_role: str,
        split_percent: float
    ) -> AttributionResult:
        """
        Upsert account partner relationship from a use case partner link.

        This creates/updates both the use_case_partners and account_partners
        tables, applying business rules and split cap enforcement.
        """
        # Find account_id from use case
        uc = self.db.read_sql("SELECT account_id FROM use_cases WHERE use_case_id = ?;", (use_case_id,))
        if uc.empty:
            raise ValueError("use_case_id not found")

        account_id = uc.loc[0, "account_id"]
        today = date.today().isoformat()

        # Upsert use_case_partner
        self.db.run_sql("""
        INSERT INTO use_case_partners(use_case_id, partner_id, partner_role, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(use_case_id, partner_id)
        DO UPDATE SET partner_role = excluded.partner_role;
        """, (use_case_id, partner_id, partner_role, today))

        # Check if manual source (don't override manual entries)
        existing = self.db.read_sql("""
            SELECT source, split_percent FROM account_partners
            WHERE account_id = ? AND partner_id = ?;
        """, (account_id, partner_id))

        old_split = None
        if not existing.empty:
            old_split = str(existing.loc[0, "split_percent"])
            if existing.loc[0, "source"] == "manual":
                logger.info(f"Skipping auto update for manual entry: {account_id}/{partner_id}")
                return AttributionResult(
                    status="skipped_manual",
                    account_id=account_id,
                    message="Manual entry not overridden"
                )

        # Check split cap
        if self.should_enforce_split_cap():
            exceeds, total_with_new = self.will_exceed_split_cap(account_id, partner_id, split_percent)
            if exceeds:
                return AttributionResult(
                    status="blocked_split_cap",
                    account_id=account_id,
                    total_with_new=total_with_new,
                    message=f"Split cap exceeded: {total_with_new:.2%}"
                )

        # Upsert account_partner
        self.db.run_sql("""
        INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source)
        VALUES (?, ?, ?, ?, ?, 'auto')
        ON CONFLICT(account_id, partner_id)
        DO UPDATE SET
            split_percent = excluded.split_percent,
            last_seen = excluded.last_seen,
            source = 'auto';
        """, (account_id, partner_id, split_percent, today, today))

        # Log audit event
        self.db.log_audit_event(
            event_type="split_updated",
            account_id=account_id,
            partner_id=partner_id,
            changed_field="split_percent",
            old_value=old_split,
            new_value=str(split_percent),
            source="auto",
            metadata={"use_case_id": use_case_id, "partner_role": partner_role}
        )

        logger.info(f"Upserted account partner: {account_id}/{partner_id} = {split_percent:.2%}")
        return AttributionResult(
            status="upserted",
            account_id=account_id,
            message="Successfully updated"
        )

    def upsert_manual_account_partner(
        self,
        account_id: str,
        partner_id: str,
        split_percent: float
    ) -> AttributionResult:
        """
        Manually set an account partner split.

        This overrides auto-calculated splits.
        """
        # Get old value for audit
        existing = self.db.read_sql("""
            SELECT split_percent FROM account_partners
            WHERE account_id = ? AND partner_id = ?;
        """, (account_id, partner_id))

        old_split = str(existing.loc[0, "split_percent"]) if not existing.empty else None

        # Check split cap
        if self.should_enforce_split_cap():
            exceeds, total_with_new = self.will_exceed_split_cap(account_id, partner_id, split_percent)
            if exceeds:
                return AttributionResult(
                    status="blocked_split_cap",
                    account_id=account_id,
                    total_with_new=total_with_new,
                    message=f"Split cap exceeded: {total_with_new:.2%}"
                )

        today = date.today().isoformat()
        self.db.run_sql("""
        INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source)
        VALUES (?, ?, ?, ?, ?, 'manual')
        ON CONFLICT(account_id, partner_id)
        DO UPDATE SET
            split_percent = excluded.split_percent,
            last_seen = excluded.last_seen,
            source = 'manual',
            first_seen = account_partners.first_seen;
        """, (account_id, partner_id, split_percent, today, today))

        # Log audit event
        self.db.log_audit_event(
            event_type="manual_split_set",
            account_id=account_id,
            partner_id=partner_id,
            changed_field="split_percent",
            old_value=old_split,
            new_value=str(split_percent),
            source="manual"
        )

        logger.info(f"Manual split set: {account_id}/{partner_id} = {split_percent:.2%}")
        return AttributionResult(
            status="upserted",
            account_id=account_id,
            message="Manual split set successfully"
        )

    def apply_rules_auto_assign(self, account_rollup_enabled: bool) -> ApplySummary:
        """
        Apply current rules to existing use_case_partner links and auto-upsert
        account_partner splits.
        """
        if not account_rollup_enabled:
            return ApplySummary(details=["Account rollup disabled for current model."])

        links = self.db.read_sql("""
            SELECT ucp.use_case_id, ucp.partner_id, ucp.partner_role,
                   u.stage, u.estimated_value, u.account_id,
                   a.account_name
            FROM use_case_partners ucp
            JOIN use_cases u ON u.use_case_id = ucp.use_case_id
            JOIN accounts a ON a.account_id = u.account_id;
        """)

        if links.empty:
            return ApplySummary(details=["No links to process."])

        # Get account totals for SI split calculation
        use_case_vals = self.db.read_sql("SELECT account_id, stage, estimated_value FROM use_cases;")
        live_totals = use_case_vals[use_case_vals["stage"] == "Live"].groupby("account_id")["estimated_value"].sum()
        all_totals = use_case_vals.groupby("account_id")["estimated_value"].sum()

        si_mode = self.db.get_setting("si_auto_split_mode", "live_share")
        defaults = {
            "Influence": float(self.db.get_setting("default_split_influence", "10")) / 100.0,
            "Referral": float(self.db.get_setting("default_split_referral", "15")) / 100.0,
            "ISV": float(self.db.get_setting("default_split_isv", "10")) / 100.0,
        }

        summary = ApplySummary()

        for _, row in links.iterrows():
            # Evaluate rules
            result = self.rule_engine.evaluate_rules({
                "partner_role": row["partner_role"],
                "stage": row["stage"],
                "estimated_value": float(row["estimated_value"] or 0),
            }, key="account_rules")

            if not result.allowed:
                summary.blocked_rule += 1
                summary.details.append(f"{row['account_name']} / {row['use_case_id']}: {result.message}")
                continue

            # Calculate split
            split = defaults.get(row["partner_role"], 0.1)

            if row["partner_role"] == "Implementation (SI)":
                acct = row["account_id"]
                uc_value = float(row["estimated_value"] or 0)
                acct_live_total = float(live_totals.get(acct, 0))
                acct_all_total = float(all_totals.get(acct, 0))
                auto_split, _ = self.compute_si_auto_split(uc_value, acct_live_total, acct_all_total, si_mode)
                if auto_split is None:
                    auto_split = float(self.db.get_setting("si_fixed_percent", "20")) / 100.0
                split = auto_split

            # Upsert
            upsert_result = self.upsert_account_partner_from_use_case_partner(
                use_case_id=row["use_case_id"],
                partner_id=row["partner_id"],
                partner_role=row["partner_role"],
                split_percent=split
            )

            if upsert_result.status == "blocked_split_cap":
                summary.blocked_cap += 1
                summary.details.append(f"{row['account_name']} / {row['use_case_id']}: blocked by split cap.")
            elif upsert_result.status == "skipped_manual":
                summary.skipped_manual += 1
            else:
                summary.applied += 1

        logger.info(f"Auto-assign complete: {summary.applied} applied, {summary.blocked_rule} blocked by rules, {summary.blocked_cap} blocked by cap")
        return summary

    def recompute_attribution_ledger(self, days: int = 30) -> LedgerResult:
        """
        Rebuild attribution_events for the last `days` days of revenue.

        This creates the ledger that shows which partners get credit for revenue.
        """
        logger.info(f"Recomputing attribution ledger for last {days} days...")
        start_date = (date.today() - timedelta(days=days)).isoformat()

        # Clear window first
        self.db.run_sql("DELETE FROM attribution_events WHERE revenue_date >= ?;", (start_date,))

        # Get revenues
        revenues = self.db.read_sql("""
            SELECT revenue_date, account_id, amount
            FROM revenue_events
            WHERE revenue_date >= ?
        """, (start_date,))

        if revenues.empty:
            logger.info("No revenue events to process")
            return LedgerResult()

        # Get account partners
        aps = self.db.read_sql("""
            SELECT ap.account_id, ap.partner_id, ap.split_percent, ap.source, p.partner_name
            FROM account_partners ap
            JOIN partners p ON p.partner_id = ap.partner_id
        """)

        if aps.empty:
            logger.info("No account partners configured")
            return LedgerResult(skipped=len(revenues))

        # Get use case partner context for rule evaluation
        ucp_context = self.db.read_sql("""
            SELECT ucp.partner_id, u.account_id, ucp.partner_role, u.stage, u.estimated_value
            FROM use_case_partners ucp
            JOIN use_cases u ON u.use_case_id = ucp.use_case_id;
        """)

        rule_ver = self.rule_engine.get_rule_version("account_rules")
        result = LedgerResult()

        for _, rev in revenues.iterrows():
            acct_id = rev["account_id"]
            amount = float(rev["amount"])
            rev_date = rev["revenue_date"]
            acct_partners = aps[aps["account_id"] == acct_id]

            if acct_partners.empty:
                result.skipped += 1
                continue

            for _, ap_row in acct_partners.iterrows():
                partner_id = ap_row["partner_id"]
                source = ap_row["source"]

                # Get context for rule evaluation
                ctx_rows = ucp_context[
                    (ucp_context["account_id"] == acct_id) & (ucp_context["partner_id"] == partner_id)
                ]
                role = ctx_rows["partner_role"].iloc[0] if not ctx_rows.empty else None
                stage_val = ctx_rows["stage"].iloc[0] if not ctx_rows.empty else None
                est_val = float(ctx_rows["estimated_value"].iloc[0]) if (not ctx_rows.empty and pd.notnull(ctx_rows["estimated_value"].iloc[0])) else None

                # Evaluate rules (skip for manual entries)
                allowed = True
                rule_name = "manual" if source == "manual" else None

                if source != "manual":
                    eval_result = self.rule_engine.evaluate_rules(
                        {"partner_role": role, "stage": stage_val, "estimated_value": est_val},
                        key="account_rules",
                    )
                    allowed = eval_result.allowed
                    rule_name = eval_result.rule_name

                    if not allowed:
                        result.blocked += 1
                        continue

                # Create attribution event
                split = float(ap_row["split_percent"])
                attr_amount = amount * split
                event_key = f"{rev_date}-{acct_id}-{partner_id}-{source}"
                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, event_key))

                self.db.run_sql("""
                    INSERT INTO attribution_events(event_id, revenue_date, account_id, actor_type, actor_id, amount, split_percent, attributed_amount, source, rule_name, rule_version, created_at)
                    VALUES (?, ?, ?, 'partner', ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO UPDATE SET
                        amount=excluded.amount,
                        split_percent=excluded.split_percent,
                        attributed_amount=excluded.attributed_amount,
                        rule_name=excluded.rule_name,
                        rule_version=excluded.rule_version,
                        created_at=excluded.created_at;
                """, (
                    event_id,
                    rev_date,
                    acct_id,
                    partner_id,
                    amount,
                    split,
                    attr_amount,
                    source,
                    rule_name,
                    rule_ver,
                    date.today().isoformat(),
                ))
                result.inserted += 1

        logger.info(f"Ledger recompute complete: {result.inserted} inserted, {result.blocked} blocked, {result.skipped} skipped")
        return result

    def simulate_rule_impact(self, key: str, days: int = 60) -> SimulationResult:
        """
        Dry-run rules against current links without mutating data.

        For account_rules, we report revenue at risk in the window.
        For use_case_rules, we report estimated value affected.
        """
        logger.info(f"Simulating rule impact for {key} over {days} days...")
        window_start = (date.today() - timedelta(days=days)).isoformat()
        results = SimulationResult(target=key, lookback_days=days)

        if key == "account_rules":
            aps = self.db.read_sql("""
                SELECT ap.account_id, ap.partner_id, ap.source, p.partner_name
                FROM account_partners ap
                JOIN partners p ON p.partner_id = ap.partner_id;
            """)

            if aps.empty:
                results.details.append("No account partners to evaluate.")
                return results

            ctx = self.db.read_sql("""
                SELECT ucp.partner_id, u.account_id, ucp.partner_role, u.stage, u.estimated_value
                FROM use_case_partners ucp
                JOIN use_cases u ON u.use_case_id = ucp.use_case_id;
            """)

            ledger = self.db.read_sql("""
                SELECT account_id, actor_id, SUM(attributed_amount) AS amt
                FROM attribution_events
                WHERE revenue_date >= ?
                GROUP BY account_id, actor_id;
            """, (window_start,))

            for _, row in aps.iterrows():
                results.checked += 1
                acct = row["account_id"]
                pid = row["partner_id"]

                ctx_rows = ctx[(ctx["account_id"] == acct) & (ctx["partner_id"] == pid)]
                role = ctx_rows["partner_role"].iloc[0] if not ctx_rows.empty else None
                stage_val = ctx_rows["stage"].iloc[0] if not ctx_rows.empty else None
                est_val = float(ctx_rows["estimated_value"].iloc[0]) if (not ctx_rows.empty and pd.notnull(ctx_rows["estimated_value"].iloc[0])) else None

                eval_result = self.rule_engine.evaluate_rules(
                    {"partner_role": role, "stage": stage_val, "estimated_value": est_val},
                    key="account_rules",
                )

                ledger_row = ledger[(ledger["account_id"] == acct) & (ledger["actor_id"] == pid)]
                amt = float(ledger_row["amt"].iloc[0]) if not ledger_row.empty else 0.0

                if eval_result.allowed:
                    results.allowed += 1
                else:
                    results.blocked += 1
                    results.revenue_at_risk += amt
                    results.details.append(
                        f"{acct}/{pid}: {eval_result.message} (rule={eval_result.rule_name or 'n/a'}, {amt:,.0f} revenue in last {days}d)"
                    )

                if ctx_rows.empty:
                    results.no_context += 1

        else:  # use_case_rules
            ucp = self.db.read_sql("""
                SELECT ucp.use_case_id, ucp.partner_id, ucp.partner_role, u.stage, u.estimated_value, u.use_case_name, u.account_id
                FROM use_case_partners ucp
                JOIN use_cases u ON u.use_case_id = ucp.use_case_id;
            """)

            if ucp.empty:
                results.details.append("No use case links to evaluate.")
                return results

            for _, row in ucp.iterrows():
                results.checked += 1
                eval_result = self.rule_engine.evaluate_rules(
                    {
                        "partner_role": row["partner_role"],
                        "stage": row["stage"],
                        "estimated_value": float(row["estimated_value"] or 0),
                    },
                    key="use_case_rules",
                )

                val = float(row["estimated_value"] or 0)

                if eval_result.allowed:
                    results.allowed += 1
                else:
                    results.blocked += 1
                    results.estimated_value_blocked += val
                    results.details.append(
                        f"{row['use_case_name']} ({row['account_id']}): {eval_result.message} "
                        f"(rule={eval_result.rule_name or 'n/a'}, est value {val:,.0f})"
                    )

        logger.info(f"Simulation complete: {results.allowed} allowed, {results.blocked} blocked")
        return results

    def recompute_explanations(self, account_id: str) -> Dict[str, int]:
        """
        Generate detailed explanations for why partners receive attribution for an account.
        """
        logger.info(f"Recomputing explanations for account {account_id}...")
        today_str = date.today().isoformat()

        aps = self.db.read_sql("""
          SELECT ap.partner_id, ap.split_percent, ap.source
          FROM account_partners ap
          WHERE ap.account_id = ?;
        """, (account_id,))

        if aps.empty:
            return {"written": 0}

        ucp = self.db.read_sql("""
          SELECT ucp.partner_id, ucp.partner_role, u.use_case_name, u.stage, u.estimated_value
          FROM use_case_partners ucp
          JOIN use_cases u ON u.use_case_id = ucp.use_case_id
          WHERE u.account_id = ?;
        """, (account_id,))

        rule_ver_use = self.rule_engine.get_rule_version("use_case_rules")
        rule_ver_account = self.rule_engine.get_rule_version("account_rules")
        written = 0

        for _, ap_row in aps.iterrows():
            pid = ap_row["partner_id"]
            uc_links = ucp[ucp["partner_id"] == pid]
            uc_items = []
            use_case_decisions = []

            for _, r in uc_links.iterrows():
                eval_result = self.rule_engine.evaluate_rules(
                    {
                        "partner_role": r["partner_role"],
                        "stage": r["stage"],
                        "estimated_value": float(r["estimated_value"] or 0),
                    },
                    key="use_case_rules",
                )

                uc_items.append({
                    "use_case_name": r["use_case_name"],
                    "role": r["partner_role"],
                    "stage": r["stage"],
                    "estimated_value": r["estimated_value"],
                    "allowed": eval_result.allowed,
                    "rule_name": eval_result.rule_name,
                    "rule_version": rule_ver_use,
                    "detail": eval_result.message,
                })
                use_case_decisions.append({
                    "use_case": r["use_case_name"],
                    "allowed": eval_result.allowed,
                    "rule_name": eval_result.rule_name
                })

            # Account rule decision
            sample_ctx = uc_links.iloc[0] if not uc_links.empty else None
            role = sample_ctx["partner_role"] if sample_ctx is not None else None
            stage_val = sample_ctx["stage"] if sample_ctx is not None else None
            est_val = float(sample_ctx["estimated_value"] or 0) if sample_ctx is not None else None

            acct_eval = self.rule_engine.evaluate_rules(
                {"partner_role": role, "stage": stage_val, "estimated_value": est_val},
                key="account_rules",
            )

            source = ap_row["source"]
            split_percent = float(ap_row["split_percent"])
            split_reason = "Manual split" if source == "manual" else "AI suggested" if source == "ai" else "Auto rollup"

            explanation = {
                "account_id": account_id,
                "partner_id": pid,
                "as_of": today_str,
                "source": source,
                "split_percent": split_percent,
                "split_reason": split_reason,
                "use_case_links": uc_items,
                "rule_decisions": {
                    "account": {
                        "allowed": acct_eval.allowed,
                        "rule_name": acct_eval.rule_name,
                        "rule_version": rule_ver_account,
                        "detail": acct_eval.message
                    },
                    "use_cases": use_case_decisions,
                },
            }

            self.db.run_sql("""
                INSERT INTO attribution_explanations(account_id, partner_id, as_of_date, explanation_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account_id, partner_id, as_of_date)
                DO UPDATE SET explanation_json=excluded.explanation_json, created_at=excluded.created_at;
            """, (account_id, pid, today_str, json.dumps(explanation, indent=2), datetime.utcnow().isoformat()))

            written += 1

        logger.info(f"Wrote {written} explanations for account {account_id}")
        return {"written": written}

    def create_use_case(
        self,
        account_id: str,
        use_case_name: str,
        stage: str,
        estimated_value: float,
        target_close_date: str,
        tag_source: str = "app"
    ) -> str:
        """Create a new use case and return its ID."""
        use_case_id = f"UC-{uuid.uuid4().hex[:8].upper()}"
        self.db.run_sql("""
        INSERT INTO use_cases(use_case_id, account_id, use_case_name, stage, estimated_value, target_close_date, tag_source)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (use_case_id, account_id, use_case_name, stage, estimated_value, target_close_date, tag_source))

        logger.info(f"Created use case {use_case_id}: {use_case_name}")
        return use_case_id
