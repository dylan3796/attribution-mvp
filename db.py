"""Database operations and schema management."""

import os
import json
import random
import sqlite3
import logging
from datetime import date, timedelta
from typing import Optional, Tuple
import uuid

import pandas as pd

from models import DEFAULT_SETTINGS, SCHEMA_VERSION

logger = logging.getLogger(__name__)


class Database:
    """Database connection and operations manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def run_sql(self, sql: str, params: tuple = ()) -> None:
        """Execute a SQL statement that modifies data."""
        try:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            conn.close()
            logger.debug(f"Executed SQL: {sql[:100]}... with params {params}")
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            raise

    def read_sql(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame."""
        try:
            conn = self.get_conn()
            df = pd.read_sql_query(sql, conn, params=params)
            conn.close()
            logger.debug(f"Read SQL: {sql[:100]}... returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error reading SQL: {e}")
            raise

    def init_db(self) -> None:
        """Initialize database schema and apply migrations."""
        logger.info("Initializing database schema...")

        # Create tables
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            account_name TEXT NOT NULL
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS partners (
            partner_id TEXT PRIMARY KEY,
            partner_name TEXT NOT NULL
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS use_cases (
            use_case_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            use_case_name TEXT NOT NULL,
            stage TEXT,
            estimated_value REAL,
            tag_source TEXT NOT NULL DEFAULT 'app',
            target_close_date TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS use_case_partners (
            use_case_id TEXT NOT NULL,
            partner_id TEXT NOT NULL,
            partner_role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (use_case_id, partner_id),
            FOREIGN KEY (use_case_id) REFERENCES use_cases(use_case_id),
            FOREIGN KEY (partner_id) REFERENCES partners(partner_id)
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS account_partners (
            account_id TEXT NOT NULL,
            partner_id TEXT NOT NULL,
            split_percent REAL NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'auto',
            PRIMARY KEY (account_id, partner_id),
            FOREIGN KEY (account_id) REFERENCES accounts(account_id),
            FOREIGN KEY (partner_id) REFERENCES partners(partner_id)
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS revenue_events (
            revenue_date TEXT NOT NULL,
            account_id TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS attribution_events (
            event_id TEXT PRIMARY KEY,
            revenue_date TEXT NOT NULL,
            account_id TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            amount REAL NOT NULL,
            split_percent REAL NOT NULL,
            attributed_amount REAL NOT NULL,
            source TEXT NOT NULL,
            rule_name TEXT,
            rule_version TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id),
            FOREIGN KEY (actor_id) REFERENCES partners(partner_id)
        );
        """)

        self.run_sql("CREATE UNIQUE INDEX IF NOT EXISTS idx_attr_events_unique ON attribution_events(revenue_date, account_id, actor_id, source);")

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS attribution_explanations (
            account_id TEXT NOT NULL,
            partner_id TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            explanation_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (account_id, partner_id, as_of_date)
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            partner_id TEXT,
            activity_type TEXT NOT NULL,
            activity_date TEXT NOT NULL,
            notes TEXT
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS ai_summaries (
            account_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            PRIMARY KEY (account_id, created_at)
        );
        """)

        self.run_sql("""
        CREATE TABLE IF NOT EXISTS ai_recommendations (
            account_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            recommendations_json TEXT NOT NULL,
            PRIMARY KEY (account_id, created_at)
        );
        """)

        # Audit trail table
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS audit_trail (
            audit_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            account_id TEXT,
            partner_id TEXT,
            changed_field TEXT,
            old_value TEXT,
            new_value TEXT,
            source TEXT,
            metadata TEXT
        );
        """)

        # ====================================================================
        # Universal Attribution System Tables (models_new.py)
        # ====================================================================

        # Attribution targets (opportunities, consumption events, etc.)
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS attribution_target (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            external_id TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT,
            name TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # Partner touchpoints (evidence of partner involvement)
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS partner_touchpoint (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            touchpoint_type TEXT NOT NULL,
            role TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            timestamp TEXT,
            source TEXT NOT NULL DEFAULT 'touchpoint_tracking',
            source_id TEXT,
            source_confidence REAL DEFAULT 1.0,
            deal_reg_status TEXT,
            deal_reg_submitted_date TEXT,
            deal_reg_approved_date TEXT,
            requires_approval INTEGER DEFAULT 0,
            approved_by TEXT,
            approval_timestamp TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (target_id) REFERENCES attribution_target(id)
        );
        """)

        # Attribution rules (configuration for calculation)
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS attribution_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            model_type TEXT NOT NULL,
            config TEXT NOT NULL,
            applies_to TEXT,
            priority INTEGER DEFAULT 100,
            split_constraint TEXT DEFAULT 'must_sum_to_100',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            created_by TEXT
        );
        """)

        # Ledger entries (attribution results)
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS ledger_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER NOT NULL,
            partner_id TEXT NOT NULL,
            attributed_value REAL NOT NULL,
            split_percentage REAL NOT NULL,
            attribution_percentage REAL NOT NULL DEFAULT 0,
            rule_id INTEGER NOT NULL,
            calculation_timestamp TEXT NOT NULL,
            override_by TEXT,
            audit_trail TEXT,
            metadata TEXT,
            FOREIGN KEY (target_id) REFERENCES attribution_target(id),
            FOREIGN KEY (rule_id) REFERENCES attribution_rule(id)
        );
        """)

        # Measurement workflows (NEW - Phase 1.5)
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS measurement_workflow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            data_sources TEXT NOT NULL,
            conflict_resolution TEXT DEFAULT 'priority',
            fallback_strategy TEXT DEFAULT 'next_priority',
            applies_to TEXT,
            is_primary INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            created_by TEXT
        );
        """)

        # Indexes for performance
        self.run_sql("CREATE INDEX IF NOT EXISTS idx_touchpoint_target ON partner_touchpoint(target_id);")
        self.run_sql("CREATE INDEX IF NOT EXISTS idx_touchpoint_partner ON partner_touchpoint(partner_id);")
        self.run_sql("CREATE INDEX IF NOT EXISTS idx_touchpoint_source ON partner_touchpoint(source);")
        self.run_sql("CREATE INDEX IF NOT EXISTS idx_ledger_target ON ledger_entry(target_id);")
        self.run_sql("CREATE INDEX IF NOT EXISTS idx_ledger_partner ON ledger_entry(partner_id);")
        self.run_sql("CREATE INDEX IF NOT EXISTS idx_workflow_company ON measurement_workflow(company_id);")

        # Apply migrations
        self._apply_migrations()

        # Migrate legacy rules
        self._migrate_legacy_rules()

        # Ensure default settings
        self._ensure_default_settings()

        logger.info("Database initialization complete")

    def _apply_migrations(self) -> None:
        """Apply lightweight migrations for existing DB files."""
        def ensure_column(table: str, column: str, definition: str):
            cols = self.read_sql(f"PRAGMA table_info({table});")["name"].tolist()
            if column not in cols:
                logger.info(f"Adding column {column} to table {table}")
                self.run_sql(f"ALTER TABLE {table} ADD COLUMN {definition};")

        # Legacy system migrations
        ensure_column("use_cases", "stage", "stage TEXT")
        ensure_column("use_cases", "estimated_value", "estimated_value REAL")
        ensure_column("use_cases", "target_close_date", "target_close_date TEXT")
        ensure_column("use_cases", "tag_source", "tag_source TEXT DEFAULT 'app'")
        ensure_column("account_partners", "source", "source TEXT NOT NULL DEFAULT 'auto'")
        ensure_column("settings", "setting_value", "setting_value TEXT NOT NULL")

        # Backfill tag_source if missing
        self.run_sql("UPDATE use_cases SET tag_source = 'app' WHERE tag_source IS NULL OR tag_source = '';")

        # ====================================================================
        # Universal Attribution System Migrations (Phase 1.3)
        # ====================================================================

        # Add new source tracking fields to partner_touchpoint
        ensure_column("partner_touchpoint", "source", "source TEXT NOT NULL DEFAULT 'touchpoint_tracking'")
        ensure_column("partner_touchpoint", "source_id", "source_id TEXT")
        ensure_column("partner_touchpoint", "source_confidence", "source_confidence REAL DEFAULT 1.0")

        # Add deal registration fields
        ensure_column("partner_touchpoint", "deal_reg_status", "deal_reg_status TEXT")
        ensure_column("partner_touchpoint", "deal_reg_submitted_date", "deal_reg_submitted_date TEXT")
        ensure_column("partner_touchpoint", "deal_reg_approved_date", "deal_reg_approved_date TEXT")

        # Add approval workflow fields
        ensure_column("partner_touchpoint", "requires_approval", "requires_approval INTEGER DEFAULT 0")
        ensure_column("partner_touchpoint", "approved_by", "approved_by TEXT")
        ensure_column("partner_touchpoint", "approval_timestamp", "approval_timestamp TEXT")

        # Backfill source field for existing touchpoints (backward compatibility)
        try:
            # Check if partner_touchpoint table exists and has records
            existing_touchpoints = self.read_sql("SELECT COUNT(*) as count FROM partner_touchpoint WHERE source IS NULL OR source = '';")
            if not existing_touchpoints.empty and existing_touchpoints.loc[0, "count"] > 0:
                logger.info("Backfilling source field for existing partner touchpoints")
                self.run_sql("""
                    UPDATE partner_touchpoint
                    SET source = CASE
                        WHEN touchpoint_type = 'manual_override' THEN 'manual_override'
                        ELSE 'touchpoint_tracking'
                    END
                    WHERE source IS NULL OR source = '';
                """)
                # Set default source_confidence for existing records
                self.run_sql("UPDATE partner_touchpoint SET source_confidence = 1.0 WHERE source_confidence IS NULL;")
        except Exception as e:
            # Table might not exist yet (fresh install)
            logger.debug(f"Skipping partner_touchpoint backfill: {e}")

        # Add missing columns to attribution_target
        ensure_column("attribution_target", "name", "name TEXT")

        # Add missing columns to ledger_entry
        ensure_column("ledger_entry", "attribution_percentage", "attribution_percentage REAL NOT NULL DEFAULT 0")
        ensure_column("ledger_entry", "metadata", "metadata TEXT")

    def _migrate_legacy_rules(self) -> None:
        """Migrate old rule_engine_rules key to account_rules."""
        existing = self.read_sql("SELECT setting_key, setting_value FROM settings WHERE setting_key = 'rule_engine_rules';")
        if not existing.empty:
            val = existing.loc[0, "setting_value"]
            # Only migrate if account_rules not already set
            if self.read_sql("SELECT setting_key FROM settings WHERE setting_key = 'account_rules';").empty:
                logger.info("Migrating legacy rules to account_rules")
                self.set_setting("account_rules", val)

    def _ensure_default_settings(self) -> None:
        """Ensure all default settings exist in the database."""
        # Add account_rules default
        DEFAULT_SETTINGS["account_rules"] = json.dumps([
            {
                "name": "Block SI below 50k estimated",
                "action": "deny",
                "when": {"partner_role": "Implementation (SI)", "max_estimated_value": 50000}
            },
            {
                "name": "Allow all fallback",
                "action": "allow",
                "when": {}
            }
        ], indent=2)

        # Add use_case_rules default
        DEFAULT_SETTINGS["use_case_rules"] = json.dumps([
            {
                "name": "Allow all use cases",
                "action": "allow",
                "when": {}
            }
        ], indent=2)

        existing_settings = self.read_sql("SELECT setting_key FROM settings;")
        for key, val in DEFAULT_SETTINGS.items():
            if key not in existing_settings["setting_key"].tolist():
                logger.info(f"Adding default setting: {key}")
                self.run_sql("INSERT INTO settings(setting_key, setting_value) VALUES (?, ?);", (key, val))

    def seed_data_if_empty(self) -> None:
        """Seed demo data if database is empty."""
        existing = self.read_sql("SELECT COUNT(*) as c FROM accounts;")
        if int(existing.loc[0, "c"]) > 0:
            logger.info("Database already has data, skipping seed")
            return

        logger.info("Seeding demo data...")

        # Seed accounts
        accounts = [
            ("A1", "Acme Corp"),
            ("A2", "Bluebird Health"),
            ("A3", "Canyon Bank"),
            ("A4", "Dune Retail"),
            ("A5", "Evergreen Manufacturing"),
        ]
        for a in accounts:
            self.run_sql("INSERT INTO accounts(account_id, account_name) VALUES (?, ?);", a)

        # Seed partners
        partners = [
            ("P1", "Titan SI"),
            ("P2", "Northwind Consulting"),
            ("P3", "Orbit ISV"),
        ]
        for p in partners:
            self.run_sql("INSERT INTO partners(partner_id, partner_name) VALUES (?, ?);", p)

        # Helper for sample estimated values
        def sample_estimated():
            if random.random() < 0.8:
                val = random.triangular(2000, 12000, 4500)
            else:
                val = random.triangular(12000, 100000, 15000)
            val = max(2000, min(100000, val))
            return int(round(val / 1000.0) * 1000)

        # Seed use cases
        use_case_specs = [
            ("UC1", "A1", "Lakehouse Migration", "Discovery", (date.today() + timedelta(days=45)).isoformat()),
            ("UC2", "A1", "GenAI Support Bot", "Evaluation", (date.today() + timedelta(days=25)).isoformat()),
            ("UC3", "A2", "Claims Modernization", "Commit", (date.today() + timedelta(days=15)).isoformat()),
            ("UC4", "A3", "Fraud Detection", "Live", (date.today() - timedelta(days=10)).isoformat()),
            ("UC5", "A4", "Real-time Personalization", "Evaluation", (date.today() + timedelta(days=30)).isoformat()),
            ("UC6", "A5", "Manufacturing QA Analytics", "Discovery", (date.today() + timedelta(days=60)).isoformat()),
        ]
        use_cases = [(uc_id, acct, name, stage, sample_estimated(), tcd, "app") for uc_id, acct, name, stage, tcd in use_case_specs]
        for uc in use_cases:
            self.run_sql("""
            INSERT INTO use_cases(use_case_id, account_id, use_case_name, stage, estimated_value, target_close_date, tag_source)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, uc)

        # Seed revenue events (last 60 days)
        start = date.today() - timedelta(days=60)
        daily = [("A1", 500), ("A2", 250), ("A3", 180), ("A4", 220), ("A5", 300)]
        for i in range(61):
            d = start + timedelta(days=i)
            for account_id, base in daily:
                self.run_sql(
                    "INSERT INTO revenue_events(revenue_date, account_id, amount) VALUES (?, ?, ?);",
                    (d.isoformat(), account_id, float(base))
                )

        # Seed activities
        self._seed_activities_if_empty()

        logger.info("Demo data seeding complete")

    def _seed_activities_if_empty(self) -> None:
        """Seed sample activities if empty."""
        existing = self.read_sql("SELECT COUNT(*) as c FROM activities;")
        if not existing.empty and int(existing.loc[0, "c"]) > 0:
            return

        sample_activities = [
            ("A1", "P1", "Workshop", (date.today() - timedelta(days=20)).isoformat(), "Data platform workshop with SI."),
            ("A1", "P2", "Referral", (date.today() - timedelta(days=10)).isoformat(), "Referral for support bot use case."),
            ("A2", "P1", "Implementation kickoff", (date.today() - timedelta(days=5)).isoformat(), "Kickoff for claims modernization."),
            ("A3", "P2", "QBR", (date.today() - timedelta(days=15)).isoformat(), "Quarterly review on fraud detection."),
            ("A4", None, "Intro meeting", (date.today() - timedelta(days=7)).isoformat(), "Intro with new ISV prospect."),
            ("A5", "P3", "Technical workshop", (date.today() - timedelta(days=3)).isoformat(), "ISV demo for manufacturing QA."),
        ]
        for acct, partner, atype, adate, notes in sample_activities:
            self.run_sql(
                "INSERT INTO activities(activity_id, account_id, partner_id, activity_type, activity_date, notes) VALUES (?, ?, ?, ?, ?, ?);",
                (str(uuid.uuid4()), acct, partner, atype, adate, notes)
            )

    # Settings helpers
    def get_setting(self, key: str, default: str) -> str:
        """Get a setting value."""
        row = self.read_sql("SELECT setting_value FROM settings WHERE setting_key = ?;", (key,))
        if row.empty:
            return default
        return str(row.loc[0, "setting_value"])

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value."""
        self.run_sql("""
        INSERT INTO settings(setting_key, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_key)
        DO UPDATE SET setting_value = excluded.setting_value;
        """, (key, value))
        logger.info(f"Setting {key} = {value}")

    def get_setting_bool(self, key: str, default: bool) -> bool:
        """Get a boolean setting value."""
        val = self.get_setting(key, str(default))
        val = str(val).lower()
        return val in ["true", "1", "yes", "on"]

    def set_setting_bool(self, key: str, value: bool) -> None:
        """Set a boolean setting value."""
        self.set_setting(key, "true" if value else "false")

    def log_audit_event(
        self,
        event_type: str,
        account_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        changed_field: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """Log an audit event."""
        from datetime import datetime
        audit_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        self.run_sql("""
        INSERT INTO audit_trail(audit_id, timestamp, event_type, account_id, partner_id, changed_field, old_value, new_value, source, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (audit_id, timestamp, event_type, account_id, partner_id, changed_field, old_value, new_value, source, metadata_json))

        logger.info(f"Audit event: {event_type} for account={account_id}, partner={partner_id}")

    def reset_demo(self) -> None:
        """Reset demo database."""
        logger.warning("Resetting demo database...")
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.init_db()
        self.seed_data_if_empty()
