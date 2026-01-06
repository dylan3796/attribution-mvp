"""
Session Manager for Streamlit Attribution App
==============================================

Bridges session state with database persistence.
Loads data from database on startup and provides methods to persist changes.
"""

import streamlit as st
from typing import List, Optional
from datetime import datetime

from repository import AttributionRepository
from models_new import (
    AttributionTarget,
    PartnerTouchpoint,
    AttributionRule,
    LedgerEntry,
    MeasurementWorkflow
)


class SessionManager:
    """Manages session state and database synchronization."""

    def __init__(self, db_path: str):
        self.repo = AttributionRepository(db_path)

    def initialize_session_state(self):
        """Initialize all session state from database."""

        # Load targets
        if "targets" not in st.session_state:
            st.session_state.targets = self.repo.get_all_targets()

        # Load touchpoints
        if "touchpoints" not in st.session_state:
            st.session_state.touchpoints = self.repo.get_all_touchpoints()

        # Load rules
        if "rules" not in st.session_state:
            st.session_state.rules = self.repo.get_all_rules()

        # Load ledger
        if "ledger" not in st.session_state:
            st.session_state.ledger = self.repo.get_all_ledger_entries()

        # Load partners
        if "partners" not in st.session_state:
            st.session_state.partners = self.repo.get_all_partners()

        # Load workflows
        if "workflows" not in st.session_state:
            st.session_state.workflows = self.repo.get_all_workflows()

        # Initialize filters (UI state only, not persisted)
        if "global_filters" not in st.session_state:
            from datetime import date, timedelta
            st.session_state.global_filters = {
                "date_range": (date.today() - timedelta(days=90), date.today()),
                "selected_partners": [],
                "deal_stage": "All",
                "min_deal_size": 0
            }

        # Initialize visible metrics (UI state only)
        if "visible_metrics" not in st.session_state:
            st.session_state.visible_metrics = {
                "revenue": True,
                "deal_count": True,
                "active_partners": True,
                "avg_deal_size": True,
                "win_rate": False,
                "deal_velocity": False
            }

    # ========================================================================
    # Target Operations
    # ========================================================================

    def add_target(self, target: AttributionTarget) -> int:
        """Add a target to database and session state."""
        # Create in database
        target_id = self.repo.create_target(target)

        # Update target with ID
        target.id = target_id

        # Add to session state
        st.session_state.targets.append(target)

        return target_id

    def update_target(self, target: AttributionTarget):
        """Update a target in database and session state."""
        # Update in database
        self.repo.update_target(target)

        # Update in session state
        for i, t in enumerate(st.session_state.targets):
            if t.id == target.id:
                st.session_state.targets[i] = target
                break

    def delete_target(self, target_id: int):
        """Delete a target from database and session state."""
        # Delete from database (cascades to touchpoints and ledger)
        self.repo.delete_target(target_id)

        # Remove from session state
        st.session_state.targets = [
            t for t in st.session_state.targets if t.id != target_id
        ]

        # Remove associated touchpoints
        st.session_state.touchpoints = [
            tp for tp in st.session_state.touchpoints if tp.target_id != target_id
        ]

        # Remove associated ledger entries
        st.session_state.ledger = [
            e for e in st.session_state.ledger if e.target_id != target_id
        ]

    def reload_targets(self):
        """Reload all targets from database."""
        st.session_state.targets = self.repo.get_all_targets()

    # ========================================================================
    # Touchpoint Operations
    # ========================================================================

    def add_touchpoint(self, touchpoint: PartnerTouchpoint) -> int:
        """Add a touchpoint to database and session state."""
        # Create in database
        touchpoint_id = self.repo.create_touchpoint(touchpoint)

        # Update touchpoint with ID
        touchpoint.id = touchpoint_id

        # Add to session state
        st.session_state.touchpoints.append(touchpoint)

        return touchpoint_id

    def add_touchpoints_bulk(self, touchpoints: List[PartnerTouchpoint]) -> List[int]:
        """Add multiple touchpoints efficiently."""
        touchpoint_ids = []

        for tp in touchpoints:
            tp_id = self.repo.create_touchpoint(tp)
            tp.id = tp_id
            st.session_state.touchpoints.append(tp)
            touchpoint_ids.append(tp_id)

        return touchpoint_ids

    def update_touchpoint(self, touchpoint: PartnerTouchpoint):
        """Update a touchpoint in database and session state."""
        # Update in database
        self.repo.update_touchpoint(touchpoint)

        # Update in session state
        for i, tp in enumerate(st.session_state.touchpoints):
            if tp.id == touchpoint.id:
                st.session_state.touchpoints[i] = touchpoint
                break

    def delete_touchpoint(self, touchpoint_id: int):
        """Delete a touchpoint from database and session state."""
        # Delete from database
        self.repo.delete_touchpoint(touchpoint_id)

        # Remove from session state
        st.session_state.touchpoints = [
            tp for tp in st.session_state.touchpoints if tp.id != touchpoint_id
        ]

    def approve_touchpoint(self, touchpoint_id: int, approved_by: str):
        """Approve a touchpoint."""
        # Update in database
        self.repo.approve_touchpoint(touchpoint_id, approved_by)

        # Update in session state
        for tp in st.session_state.touchpoints:
            if tp.id == touchpoint_id:
                tp.approved_by = approved_by
                tp.approval_timestamp = datetime.now()
                tp.deal_reg_status = "approved"
                tp.deal_reg_approved_date = datetime.now()
                break

    def reject_touchpoint(self, touchpoint_id: int, rejected_by: str, reason: str):
        """Reject a touchpoint."""
        # Update in database
        self.repo.reject_touchpoint(touchpoint_id, rejected_by, reason)

        # Update in session state
        for tp in st.session_state.touchpoints:
            if tp.id == touchpoint_id:
                tp.deal_reg_status = "rejected"
                tp.metadata['rejection_reason'] = reason
                tp.metadata['rejected_by'] = rejected_by
                tp.metadata['rejected_at'] = datetime.now().isoformat()
                break

    def get_pending_approvals(self) -> List[PartnerTouchpoint]:
        """Get all touchpoints requiring approval."""
        return self.repo.get_pending_approvals()

    def reload_touchpoints(self):
        """Reload all touchpoints from database."""
        st.session_state.touchpoints = self.repo.get_all_touchpoints()

    # ========================================================================
    # Rule Operations
    # ========================================================================

    def add_rule(self, rule: AttributionRule) -> int:
        """Add a rule to database and session state."""
        # Create in database
        rule_id = self.repo.create_rule(rule)

        # Update rule with ID
        rule.id = rule_id

        # Add to session state
        st.session_state.rules.append(rule)

        return rule_id

    def update_rule(self, rule: AttributionRule):
        """Update a rule in database and session state."""
        # Update in database
        self.repo.update_rule(rule)

        # Update in session state
        for i, r in enumerate(st.session_state.rules):
            if r.id == rule.id:
                st.session_state.rules[i] = rule
                break

    def delete_rule(self, rule_id: int):
        """Delete a rule from database and session state."""
        # Delete from database
        self.repo.delete_rule(rule_id)

        # Remove from session state
        st.session_state.rules = [
            r for r in st.session_state.rules if r.id != rule_id
        ]

    def reload_rules(self):
        """Reload all rules from database."""
        st.session_state.rules = self.repo.get_all_rules()

    # ========================================================================
    # Ledger Operations
    # ========================================================================

    def add_ledger_entry(self, entry: LedgerEntry) -> int:
        """Add a ledger entry to database and session state."""
        # Create in database
        entry_id = self.repo.create_ledger_entry(entry)

        # Update entry with ID
        entry.id = entry_id

        # Add to session state
        st.session_state.ledger.append(entry)

        return entry_id

    def add_ledger_entries_bulk(self, entries: List[LedgerEntry]) -> List[int]:
        """Add multiple ledger entries efficiently."""
        entry_ids = []

        for entry in entries:
            entry_id = self.repo.create_ledger_entry(entry)
            entry.id = entry_id
            st.session_state.ledger.append(entry)
            entry_ids.append(entry_id)

        return entry_ids

    def clear_ledger(self):
        """Clear all ledger entries."""
        # Clear database
        self.repo.clear_ledger()

        # Clear session state
        st.session_state.ledger = []

    def reload_ledger(self):
        """Reload all ledger entries from database."""
        st.session_state.ledger = self.repo.get_all_ledger_entries()

    # ========================================================================
    # Workflow Operations
    # ========================================================================

    def add_workflow(self, workflow: MeasurementWorkflow) -> int:
        """Add a workflow to database and session state."""
        # Create in database
        workflow_id = self.repo.create_workflow(workflow)

        # Update workflow with ID
        workflow.id = workflow_id

        # Add to session state
        st.session_state.workflows.append(workflow)

        return workflow_id

    def update_workflow(self, workflow: MeasurementWorkflow):
        """Update a workflow in database and session state."""
        # Update in database
        self.repo.update_workflow(workflow)

        # Update in session state
        for i, w in enumerate(st.session_state.workflows):
            if w.id == workflow.id:
                st.session_state.workflows[i] = workflow
                break

    def delete_workflow(self, workflow_id: int):
        """Delete a workflow from database and session state."""
        # Delete from database
        self.repo.delete_workflow(workflow_id)

        # Remove from session state
        st.session_state.workflows = [
            w for w in st.session_state.workflows if w.id != workflow_id
        ]

    def reload_workflows(self):
        """Reload all workflows from database."""
        st.session_state.workflows = self.repo.get_all_workflows()

    # ========================================================================
    # Partner Operations
    # ========================================================================

    def add_partner(self, partner_id: str, partner_name: str):
        """Add a partner to database and session state."""
        # Create in database
        self.repo.create_partner(partner_id, partner_name)

        # Add to session state
        st.session_state.partners[partner_id] = partner_name

    def update_partner(self, partner_id: str, partner_name: str):
        """Update a partner in database and session state."""
        # Update in database
        self.repo.update_partner(partner_id, partner_name)

        # Update in session state
        st.session_state.partners[partner_id] = partner_name

    def delete_partner(self, partner_id: str):
        """Delete a partner from database and session state."""
        # Delete from database
        self.repo.delete_partner(partner_id)

        # Remove from session state
        if partner_id in st.session_state.partners:
            del st.session_state.partners[partner_id]

    def reload_partners(self):
        """Reload all partners from database."""
        st.session_state.partners = self.repo.get_all_partners()

    # ========================================================================
    # Recalculation
    # ========================================================================

    def recalculate_attribution(self, attribution_engine):
        """
        Recalculate all attribution and persist to database.

        This replaces the current in-memory recalculation with database persistence.
        """
        from attribution_engine import select_rule_for_target

        # Clear existing ledger
        self.clear_ledger()

        new_entries = []

        # Calculate attribution for each target
        for target in st.session_state.targets:
            # Get touchpoints for this target
            target_touchpoints = [
                tp for tp in st.session_state.touchpoints
                if tp.target_id == target.id
            ]

            if not target_touchpoints:
                continue

            # Select rule
            rule = select_rule_for_target(target, st.session_state.rules)
            if not rule:
                continue

            # Calculate attribution
            entries = attribution_engine.calculate(
                target,
                target_touchpoints,
                rule
            )

            new_entries.extend(entries)

        # Persist all entries to database
        self.add_ledger_entries_bulk(new_entries)

        return len(new_entries)
