"""
Database Repository Layer for Universal Attribution System
=============================================================

Provides persistent storage and retrieval for all attribution entities,
replacing session state with proper database persistence.
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from models_new import (
    AttributionTarget,
    PartnerTouchpoint,
    AttributionRule,
    LedgerEntry,
    MeasurementWorkflow,
    DataSourceConfig,
    DataSource,
    AttributionModel,
    TargetType,
    TouchpointType
)


class AttributionRepository:
    """Repository for managing attribution data in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        self.conn.close()

    # ========================================================================
    # Attribution Targets
    # ========================================================================

    def create_target(self, target: AttributionTarget) -> int:
        """Create a new attribution target and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO attribution_target (type, external_id, value, timestamp, metadata, name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            target.type.value,
            target.external_id,
            target.value,
            target.timestamp.isoformat() if target.timestamp else None,
            json.dumps(target.metadata),
            target.name,
            target.created_at.isoformat()
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_target(self, target_id: int) -> Optional[AttributionTarget]:
        """Get a target by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM attribution_target WHERE id = ?", (target_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return AttributionTarget(
            id=row['id'],
            type=TargetType(row['type']),
            external_id=row['external_id'],
            value=row['value'],
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            name=row['name'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def get_all_targets(self) -> List[AttributionTarget]:
        """Get all attribution targets."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM attribution_target ORDER BY created_at DESC")
        rows = cursor.fetchall()

        targets = []
        for row in rows:
            targets.append(AttributionTarget(
                id=row['id'],
                type=TargetType(row['type']),
                external_id=row['external_id'],
                value=row['value'],
                timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at'])
            ))

        return targets

    def update_target(self, target: AttributionTarget) -> None:
        """Update an existing target."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE attribution_target
            SET type = ?, external_id = ?, value = ?, timestamp = ?, metadata = ?, name = ?
            WHERE id = ?
        """, (
            target.type.value,
            target.external_id,
            target.value,
            target.timestamp.isoformat() if target.timestamp else None,
            json.dumps(target.metadata),
            target.name,
            target.id
        ))
        self.conn.commit()

    def delete_target(self, target_id: int) -> None:
        """Delete a target and all associated touchpoints and ledger entries."""
        cursor = self.conn.cursor()

        # Delete associated touchpoints
        cursor.execute("DELETE FROM partner_touchpoint WHERE target_id = ?", (target_id,))

        # Delete associated ledger entries
        cursor.execute("DELETE FROM ledger_entry WHERE target_id = ?", (target_id,))

        # Delete target
        cursor.execute("DELETE FROM attribution_target WHERE id = ?", (target_id,))

        self.conn.commit()

    # ========================================================================
    # Partner Touchpoints
    # ========================================================================

    def create_touchpoint(self, touchpoint: PartnerTouchpoint) -> int:
        """Create a new partner touchpoint and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO partner_touchpoint (
                partner_id, target_id, touchpoint_type, role, weight, timestamp,
                source, source_id, source_confidence,
                deal_reg_status, deal_reg_submitted_date, deal_reg_approved_date,
                requires_approval, approved_by, approval_timestamp,
                metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            touchpoint.partner_id,
            touchpoint.target_id,
            touchpoint.touchpoint_type.value,
            touchpoint.role,
            touchpoint.weight,
            touchpoint.timestamp.isoformat() if touchpoint.timestamp else None,
            touchpoint.source.value,
            touchpoint.source_id,
            touchpoint.source_confidence,
            touchpoint.deal_reg_status,
            touchpoint.deal_reg_submitted_date.isoformat() if touchpoint.deal_reg_submitted_date else None,
            touchpoint.deal_reg_approved_date.isoformat() if touchpoint.deal_reg_approved_date else None,
            1 if touchpoint.requires_approval else 0,
            touchpoint.approved_by,
            touchpoint.approval_timestamp.isoformat() if touchpoint.approval_timestamp else None,
            json.dumps(touchpoint.metadata),
            touchpoint.created_at.isoformat()
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_touchpoint(self, touchpoint_id: int) -> Optional[PartnerTouchpoint]:
        """Get a touchpoint by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM partner_touchpoint WHERE id = ?", (touchpoint_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_touchpoint(row)

    def get_touchpoints_for_target(self, target_id: int) -> List[PartnerTouchpoint]:
        """Get all touchpoints for a target."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM partner_touchpoint WHERE target_id = ?", (target_id,))
        rows = cursor.fetchall()

        return [self._row_to_touchpoint(row) for row in rows]

    def get_all_touchpoints(self) -> List[PartnerTouchpoint]:
        """Get all partner touchpoints."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM partner_touchpoint ORDER BY created_at DESC")
        rows = cursor.fetchall()

        return [self._row_to_touchpoint(row) for row in rows]

    def get_pending_approvals(self) -> List[PartnerTouchpoint]:
        """Get all touchpoints requiring approval."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM partner_touchpoint
            WHERE requires_approval = 1 AND approved_by IS NULL
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()

        return [self._row_to_touchpoint(row) for row in rows]

    def approve_touchpoint(self, touchpoint_id: int, approved_by: str) -> None:
        """Approve a touchpoint."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE partner_touchpoint
            SET approved_by = ?, approval_timestamp = ?, deal_reg_status = 'approved',
                deal_reg_approved_date = ?
            WHERE id = ?
        """, (
            approved_by,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            touchpoint_id
        ))
        self.conn.commit()

    def reject_touchpoint(self, touchpoint_id: int, rejected_by: str, reason: str) -> None:
        """Reject a touchpoint."""
        cursor = self.conn.cursor()

        # Get current metadata
        cursor.execute("SELECT metadata FROM partner_touchpoint WHERE id = ?", (touchpoint_id,))
        row = cursor.fetchone()
        metadata = json.loads(row['metadata']) if row and row['metadata'] else {}

        # Add rejection info
        metadata['rejection_reason'] = reason
        metadata['rejected_by'] = rejected_by
        metadata['rejected_at'] = datetime.now().isoformat()

        cursor.execute("""
            UPDATE partner_touchpoint
            SET deal_reg_status = 'rejected', metadata = ?
            WHERE id = ?
        """, (json.dumps(metadata), touchpoint_id))
        self.conn.commit()

    def update_touchpoint(self, touchpoint: PartnerTouchpoint) -> None:
        """Update an existing touchpoint."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE partner_touchpoint
            SET partner_id = ?, target_id = ?, touchpoint_type = ?, role = ?,
                weight = ?, timestamp = ?, source = ?, source_id = ?,
                source_confidence = ?, deal_reg_status = ?,
                deal_reg_submitted_date = ?, deal_reg_approved_date = ?,
                requires_approval = ?, approved_by = ?, approval_timestamp = ?,
                metadata = ?
            WHERE id = ?
        """, (
            touchpoint.partner_id,
            touchpoint.target_id,
            touchpoint.touchpoint_type.value,
            touchpoint.role,
            touchpoint.weight,
            touchpoint.timestamp.isoformat() if touchpoint.timestamp else None,
            touchpoint.source.value,
            touchpoint.source_id,
            touchpoint.source_confidence,
            touchpoint.deal_reg_status,
            touchpoint.deal_reg_submitted_date.isoformat() if touchpoint.deal_reg_submitted_date else None,
            touchpoint.deal_reg_approved_date.isoformat() if touchpoint.deal_reg_approved_date else None,
            1 if touchpoint.requires_approval else 0,
            touchpoint.approved_by,
            touchpoint.approval_timestamp.isoformat() if touchpoint.approval_timestamp else None,
            json.dumps(touchpoint.metadata),
            touchpoint.id
        ))
        self.conn.commit()

    def delete_touchpoint(self, touchpoint_id: int) -> None:
        """Delete a touchpoint."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM partner_touchpoint WHERE id = ?", (touchpoint_id,))
        self.conn.commit()

    def _row_to_touchpoint(self, row: sqlite3.Row) -> PartnerTouchpoint:
        """Convert database row to PartnerTouchpoint object."""
        return PartnerTouchpoint(
            id=row['id'],
            partner_id=row['partner_id'],
            target_id=row['target_id'],
            touchpoint_type=TouchpointType(row['touchpoint_type']),
            role=row['role'],
            weight=row['weight'],
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
            source=DataSource(row['source']),
            source_id=row['source_id'],
            source_confidence=row['source_confidence'],
            deal_reg_status=row['deal_reg_status'],
            deal_reg_submitted_date=datetime.fromisoformat(row['deal_reg_submitted_date']) if row['deal_reg_submitted_date'] else None,
            deal_reg_approved_date=datetime.fromisoformat(row['deal_reg_approved_date']) if row['deal_reg_approved_date'] else None,
            requires_approval=bool(row['requires_approval']),
            approved_by=row['approved_by'],
            approval_timestamp=datetime.fromisoformat(row['approval_timestamp']) if row['approval_timestamp'] else None,
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            created_at=datetime.fromisoformat(row['created_at'])
        )

    # ========================================================================
    # Attribution Rules
    # ========================================================================

    def create_rule(self, rule: AttributionRule) -> int:
        """Create a new attribution rule and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO attribution_rule (
                name, model_type, config, applies_to, priority, split_constraint,
                active, created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.name,
            rule.model_type.value,
            json.dumps(rule.config),
            json.dumps(rule.applies_to) if rule.applies_to else None,
            rule.priority,
            rule.split_constraint,
            1 if rule.active else 0,
            rule.created_at.isoformat(),
            rule.created_by
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_rule(self, rule_id: int) -> Optional[AttributionRule]:
        """Get a rule by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM attribution_rule WHERE id = ?", (rule_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_rule(row)

    def get_all_rules(self) -> List[AttributionRule]:
        """Get all attribution rules."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM attribution_rule ORDER BY priority ASC, created_at DESC")
        rows = cursor.fetchall()

        return [self._row_to_rule(row) for row in rows]

    def get_active_rules(self) -> List[AttributionRule]:
        """Get all active attribution rules."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM attribution_rule
            WHERE active = 1
            ORDER BY priority ASC, created_at DESC
        """)
        rows = cursor.fetchall()

        return [self._row_to_rule(row) for row in rows]

    def update_rule(self, rule: AttributionRule) -> None:
        """Update an existing rule."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE attribution_rule
            SET name = ?, model_type = ?, config = ?, applies_to = ?,
                priority = ?, split_constraint = ?, active = ?
            WHERE id = ?
        """, (
            rule.name,
            rule.model_type.value,
            json.dumps(rule.config),
            json.dumps(rule.applies_to) if rule.applies_to else None,
            rule.priority,
            rule.split_constraint,
            1 if rule.active else 0,
            rule.id
        ))
        self.conn.commit()

    def delete_rule(self, rule_id: int) -> None:
        """Delete a rule."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM attribution_rule WHERE id = ?", (rule_id,))
        self.conn.commit()

    def _row_to_rule(self, row: sqlite3.Row) -> AttributionRule:
        """Convert database row to AttributionRule object."""
        return AttributionRule(
            id=row['id'],
            name=row['name'],
            model_type=AttributionModel(row['model_type']),
            config=json.loads(row['config']),
            applies_to=json.loads(row['applies_to']) if row['applies_to'] else {},
            priority=row['priority'],
            split_constraint=row['split_constraint'],
            active=bool(row['active']),
            created_at=datetime.fromisoformat(row['created_at']),
            created_by=row['created_by']
        )

    # ========================================================================
    # Ledger Entries
    # ========================================================================

    def create_ledger_entry(self, entry: LedgerEntry) -> int:
        """Create a new ledger entry and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ledger_entry (
                target_id, partner_id, attributed_value, split_percentage,
                attribution_percentage, rule_id, calculation_timestamp,
                override_by, audit_trail, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.target_id,
            entry.partner_id,
            entry.attributed_value,
            entry.split_percentage,
            entry.attribution_percentage,
            entry.rule_id,
            entry.calculation_timestamp.isoformat(),
            entry.override_by,
            json.dumps(entry.audit_trail),
            json.dumps(entry.metadata)
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_ledger_entry(self, entry_id: int) -> Optional[LedgerEntry]:
        """Get a ledger entry by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ledger_entry WHERE id = ?", (entry_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_ledger_entry(row)

    def get_all_ledger_entries(self) -> List[LedgerEntry]:
        """Get all ledger entries."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ledger_entry ORDER BY calculation_timestamp DESC")
        rows = cursor.fetchall()

        return [self._row_to_ledger_entry(row) for row in rows]

    def get_ledger_entries_for_target(self, target_id: int) -> List[LedgerEntry]:
        """Get all ledger entries for a target."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ledger_entry WHERE target_id = ?", (target_id,))
        rows = cursor.fetchall()

        return [self._row_to_ledger_entry(row) for row in rows]

    def get_ledger_entries_for_partner(self, partner_id: str) -> List[LedgerEntry]:
        """Get all ledger entries for a partner."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ledger_entry WHERE partner_id = ?", (partner_id,))
        rows = cursor.fetchall()

        return [self._row_to_ledger_entry(row) for row in rows]

    def clear_ledger(self) -> None:
        """Clear all ledger entries."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM ledger_entry")
        self.conn.commit()

    def _row_to_ledger_entry(self, row: sqlite3.Row) -> LedgerEntry:
        """Convert database row to LedgerEntry object."""
        return LedgerEntry(
            id=row['id'],
            target_id=row['target_id'],
            partner_id=row['partner_id'],
            attributed_value=row['attributed_value'],
            split_percentage=row['split_percentage'],
            attribution_percentage=row['attribution_percentage'],
            rule_id=row['rule_id'],
            calculation_timestamp=datetime.fromisoformat(row['calculation_timestamp']),
            override_by=row['override_by'],
            audit_trail=json.loads(row['audit_trail']),
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )

    # ========================================================================
    # Measurement Workflows
    # ========================================================================

    def create_workflow(self, workflow: MeasurementWorkflow) -> int:
        """Create a new measurement workflow and return its ID."""
        cursor = self.conn.cursor()

        # Serialize data sources
        data_sources_json = json.dumps([
            {
                'source_type': ds.source_type.value,
                'enabled': ds.enabled,
                'priority': ds.priority,
                'auto_create_touchpoints': ds.auto_create_touchpoints,
                'requires_validation': ds.requires_validation,
                'config': ds.config
            }
            for ds in workflow.data_sources
        ])

        cursor.execute("""
            INSERT INTO measurement_workflow (
                company_id, name, description, data_sources,
                conflict_resolution, fallback_strategy, applies_to,
                is_primary, active, created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow.company_id,
            workflow.name,
            workflow.description,
            data_sources_json,
            workflow.conflict_resolution,
            workflow.fallback_strategy,
            json.dumps(workflow.applies_to),
            1 if workflow.is_primary else 0,
            1 if workflow.active else 0,
            workflow.created_at.isoformat(),
            workflow.created_by
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_workflow(self, workflow_id: int) -> Optional[MeasurementWorkflow]:
        """Get a workflow by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM measurement_workflow WHERE id = ?", (workflow_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_workflow(row)

    def get_all_workflows(self) -> List[MeasurementWorkflow]:
        """Get all measurement workflows."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM measurement_workflow ORDER BY is_primary DESC, created_at DESC")
        rows = cursor.fetchall()

        return [self._row_to_workflow(row) for row in rows]

    def get_primary_workflow(self, company_id: str) -> Optional[MeasurementWorkflow]:
        """Get the primary workflow for a company."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM measurement_workflow
            WHERE company_id = ? AND is_primary = 1 AND active = 1
            LIMIT 1
        """, (company_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_workflow(row)

    def update_workflow(self, workflow: MeasurementWorkflow) -> None:
        """Update an existing workflow."""
        cursor = self.conn.cursor()

        # Serialize data sources
        data_sources_json = json.dumps([
            {
                'source_type': ds.source_type.value,
                'enabled': ds.enabled,
                'priority': ds.priority,
                'auto_create_touchpoints': ds.auto_create_touchpoints,
                'requires_validation': ds.requires_validation,
                'config': ds.config
            }
            for ds in workflow.data_sources
        ])

        cursor.execute("""
            UPDATE measurement_workflow
            SET name = ?, description = ?, data_sources = ?,
                conflict_resolution = ?, fallback_strategy = ?,
                applies_to = ?, is_primary = ?, active = ?
            WHERE id = ?
        """, (
            workflow.name,
            workflow.description,
            data_sources_json,
            workflow.conflict_resolution,
            workflow.fallback_strategy,
            json.dumps(workflow.applies_to),
            1 if workflow.is_primary else 0,
            1 if workflow.active else 0,
            workflow.id
        ))
        self.conn.commit()

    def delete_workflow(self, workflow_id: int) -> None:
        """Delete a workflow."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM measurement_workflow WHERE id = ?", (workflow_id,))
        self.conn.commit()

    def _row_to_workflow(self, row: sqlite3.Row) -> MeasurementWorkflow:
        """Convert database row to MeasurementWorkflow object."""
        data_sources_data = json.loads(row['data_sources'])
        data_sources = [
            DataSourceConfig(
                source_type=DataSource(ds['source_type']),
                enabled=ds['enabled'],
                priority=ds['priority'],
                auto_create_touchpoints=ds.get('auto_create_touchpoints', True),
                requires_validation=ds.get('requires_validation', False),
                config=ds.get('config', {})
            )
            for ds in data_sources_data
        ]

        return MeasurementWorkflow(
            id=row['id'],
            company_id=row['company_id'],
            name=row['name'],
            description=row['description'],
            data_sources=data_sources,
            conflict_resolution=row['conflict_resolution'],
            fallback_strategy=row['fallback_strategy'],
            applies_to=json.loads(row['applies_to']) if row['applies_to'] else {},
            is_primary=bool(row['is_primary']),
            active=bool(row['active']),
            created_at=datetime.fromisoformat(row['created_at']),
            created_by=row['created_by']
        )

    # ========================================================================
    # Partners
    # ========================================================================

    def get_all_partners(self) -> Dict[str, str]:
        """Get all partners as a dict of {partner_id: partner_name}."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT partner_id, partner_name FROM partners")
        rows = cursor.fetchall()

        return {row['partner_id']: row['partner_name'] for row in rows}

    def create_partner(self, partner_id: str, partner_name: str) -> None:
        """Create a new partner."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO partners (partner_id, partner_name)
            VALUES (?, ?)
        """, (partner_id, partner_name))
        self.conn.commit()

    def update_partner(self, partner_id: str, partner_name: str) -> None:
        """Update a partner's name."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE partners SET partner_name = ? WHERE partner_id = ?
        """, (partner_name, partner_id))
        self.conn.commit()

    def delete_partner(self, partner_id: str) -> None:
        """Delete a partner."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM partners WHERE partner_id = ?", (partner_id,))
        self.conn.commit()

    # ========================================================================
    # Attribution Periods
    # ========================================================================

    def create_period(self, period: 'AttributionPeriod') -> int:
        """Create a new attribution period and return its ID."""
        from models_new import AttributionPeriod, PeriodType, PeriodStatus

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO attribution_period (
                organization_id, name, period_type, start_date, end_date,
                status, closed_at, closed_by, locked_at, locked_by,
                total_revenue, total_deals, total_partners,
                created_at, created_by, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            period.organization_id,
            period.name,
            period.period_type.value,
            period.start_date.isoformat(),
            period.end_date.isoformat(),
            period.status.value,
            period.closed_at.isoformat() if period.closed_at else None,
            period.closed_by,
            period.locked_at.isoformat() if period.locked_at else None,
            period.locked_by,
            period.total_revenue,
            period.total_deals,
            period.total_partners,
            period.created_at.isoformat(),
            period.created_by,
            period.notes
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_period(self, period_id: int) -> Optional['AttributionPeriod']:
        """Get a period by ID."""
        from models_new import AttributionPeriod, PeriodType, PeriodStatus

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM attribution_period WHERE id = ?", (period_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return AttributionPeriod(
            id=row['id'],
            organization_id=row['organization_id'],
            name=row['name'],
            period_type=PeriodType(row['period_type']),
            start_date=datetime.fromisoformat(row['start_date']),
            end_date=datetime.fromisoformat(row['end_date']),
            status=PeriodStatus(row['status']),
            closed_at=datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None,
            closed_by=row['closed_by'],
            locked_at=datetime.fromisoformat(row['locked_at']) if row['locked_at'] else None,
            locked_by=row['locked_by'],
            total_revenue=row['total_revenue'],
            total_deals=row['total_deals'],
            total_partners=row['total_partners'],
            created_at=datetime.fromisoformat(row['created_at']),
            created_by=row['created_by'],
            notes=row['notes']
        )

    def get_all_periods(self, organization_id: str) -> List['AttributionPeriod']:
        """Get all periods for an organization."""
        from models_new import AttributionPeriod, PeriodType, PeriodStatus

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM attribution_period
            WHERE organization_id = ?
            ORDER BY start_date DESC
        """, (organization_id,))
        rows = cursor.fetchall()

        periods = []
        for row in rows:
            periods.append(AttributionPeriod(
                id=row['id'],
                organization_id=row['organization_id'],
                name=row['name'],
                period_type=PeriodType(row['period_type']),
                start_date=datetime.fromisoformat(row['start_date']),
                end_date=datetime.fromisoformat(row['end_date']),
                status=PeriodStatus(row['status']),
                closed_at=datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None,
                closed_by=row['closed_by'],
                locked_at=datetime.fromisoformat(row['locked_at']) if row['locked_at'] else None,
                locked_by=row['locked_by'],
                total_revenue=row['total_revenue'],
                total_deals=row['total_deals'],
                total_partners=row['total_partners'],
                created_at=datetime.fromisoformat(row['created_at']),
                created_by=row['created_by'],
                notes=row['notes']
            ))

        return periods

    def get_current_period(self, organization_id: str) -> Optional['AttributionPeriod']:
        """Get the current open period for an organization."""
        from models_new import AttributionPeriod, PeriodType, PeriodStatus

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM attribution_period
            WHERE organization_id = ? AND status = 'open'
            ORDER BY start_date DESC
            LIMIT 1
        """, (organization_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return AttributionPeriod(
            id=row['id'],
            organization_id=row['organization_id'],
            name=row['name'],
            period_type=PeriodType(row['period_type']),
            start_date=datetime.fromisoformat(row['start_date']),
            end_date=datetime.fromisoformat(row['end_date']),
            status=PeriodStatus(row['status']),
            closed_at=datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None,
            closed_by=row['closed_by'],
            locked_at=datetime.fromisoformat(row['locked_at']) if row['locked_at'] else None,
            locked_by=row['locked_by'],
            total_revenue=row['total_revenue'],
            total_deals=row['total_deals'],
            total_partners=row['total_partners'],
            created_at=datetime.fromisoformat(row['created_at']),
            created_by=row['created_by'],
            notes=row['notes']
        )

    def close_period(self, period_id: int, closed_by: str, total_revenue: float, total_deals: int, total_partners: int) -> None:
        """Close a period and record summary statistics."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE attribution_period
            SET status = 'closed',
                closed_at = ?,
                closed_by = ?,
                total_revenue = ?,
                total_deals = ?,
                total_partners = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            closed_by,
            total_revenue,
            total_deals,
            total_partners,
            period_id
        ))
        self.conn.commit()

    def lock_period(self, period_id: int, locked_by: str) -> None:
        """Lock a period to prevent any modifications."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE attribution_period
            SET status = 'locked',
                locked_at = ?,
                locked_by = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            locked_by,
            period_id
        ))
        self.conn.commit()

    def reopen_period(self, period_id: int) -> None:
        """Reopen a closed period."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE attribution_period
            SET status = 'open',
                closed_at = NULL,
                closed_by = NULL,
                locked_at = NULL,
                locked_by = NULL
            WHERE id = ?
        """, (period_id,))
        self.conn.commit()

    def update_period(self, period: 'AttributionPeriod') -> None:
        """Update a period."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE attribution_period
            SET name = ?, period_type = ?, start_date = ?, end_date = ?,
                status = ?, notes = ?
            WHERE id = ?
        """, (
            period.name,
            period.period_type.value,
            period.start_date.isoformat(),
            period.end_date.isoformat(),
            period.status.value,
            period.notes,
            period.id
        ))
        self.conn.commit()

    def delete_period(self, period_id: int) -> None:
        """Delete a period."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM attribution_period WHERE id = ?", (period_id,))
        self.conn.commit()
