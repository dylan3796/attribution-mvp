"""
Universal Database Manager
==========================

Supports both SQLite (local development) and PostgreSQL (production).
Automatically detects which database to use and handles schema creation.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Any, Dict
import streamlit as st

from db_connection import get_connection, is_postgres, DatabaseAdapter

logger = logging.getLogger(__name__)


class Database:
    """Universal database manager supporting SQLite and PostgreSQL."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database (ignored if using PostgreSQL)
        """
        self.db_path = db_path
        self.is_postgres = is_postgres()

        # Get connection
        self.conn = get_connection()
        self.adapter = DatabaseAdapter(self.conn)

        logger.info(f"Database initialized: {'PostgreSQL' if self.is_postgres else 'SQLite'}")

    def get_conn(self):
        """Get database connection."""
        if not hasattr(self, 'conn') or self.conn is None:
            self.conn = get_connection()
        return self.conn

    def run_sql(self, sql: str, params: tuple = ()) -> None:
        """Execute SQL statement."""
        try:
            cursor = self.adapter.execute(sql, params)
            self.adapter.commit()
            logger.debug(f"Executed SQL: {sql[:100]}...")
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            self.adapter.rollback()
            raise

    def execute_with_return(self, sql: str, params: tuple = ()):
        """Execute SQL and return cursor (for INSERT...RETURNING)."""
        try:
            cursor = self.adapter.execute(sql, params)
            self.adapter.commit()
            return cursor
        except Exception as e:
            logger.error(f"Error executing SQL with return: {e}")
            self.adapter.rollback()
            raise

    def init_db(self) -> None:
        """Initialize database schema."""
        logger.info("Initializing database schema...")

        # Determine SQL syntax based on database type
        if self.is_postgres:
            pk = "SERIAL PRIMARY KEY"
            timestamp_type = "TIMESTAMP"
            bool_type = "BOOLEAN"
            default_timestamp = "CURRENT_TIMESTAMP"
        else:
            pk = "INTEGER PRIMARY KEY AUTOINCREMENT"
            timestamp_type = "TEXT"
            bool_type = "INTEGER"
            default_timestamp = "CURRENT_TIMESTAMP"

        # Organizations table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at {timestamp_type} DEFAULT {default_timestamp}
        );
        """)

        # Users table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS users (
            id {pk},
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            is_active {bool_type} DEFAULT {'TRUE' if self.is_postgres else '1'},
            created_at {timestamp_type} DEFAULT {default_timestamp},
            last_login {timestamp_type},
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        );
        """)

        # Sessions table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at {timestamp_type} DEFAULT {default_timestamp},
            expires_at {timestamp_type} NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)

        # Attribution Target table (enhanced with revenue type classification)
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS attribution_target (
            id {pk},
            external_id TEXT NOT NULL,
            name TEXT,
            type TEXT NOT NULL,
            value REAL NOT NULL,
            revenue_type TEXT,
            account_id TEXT,
            account_name TEXT,
            created_at {timestamp_type} DEFAULT {default_timestamp},
            metadata TEXT
        );
        """)

        # Partner Touchpoint table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS partner_touchpoint (
            id {pk},
            partner_id TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            touchpoint_type TEXT NOT NULL,
            role TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            timestamp {timestamp_type},
            source TEXT DEFAULT 'touchpoint_tracking',
            source_id TEXT,
            source_confidence REAL DEFAULT 1.0,
            deal_reg_status TEXT,
            deal_reg_submitted_date {timestamp_type},
            deal_reg_approved_date {timestamp_type},
            requires_approval {bool_type} DEFAULT {'FALSE' if self.is_postgres else '0'},
            approved_by TEXT,
            approval_timestamp {timestamp_type},
            metadata TEXT,
            created_at {timestamp_type} DEFAULT {default_timestamp},
            FOREIGN KEY (target_id) REFERENCES attribution_target(id)
        );
        """)

        # Universal Touchpoint table (supports any actor type: partner, campaign, sales_rep, etc.)
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS touchpoint (
            id {pk},
            actor_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            actor_name TEXT,
            target_id INTEGER NOT NULL,
            touchpoint_type TEXT NOT NULL,
            role TEXT,
            weight REAL DEFAULT 1.0,
            timestamp {timestamp_type},
            source TEXT DEFAULT 'touchpoint_tracking',
            source_id TEXT,
            source_confidence REAL DEFAULT 1.0,
            requires_approval {bool_type} DEFAULT {'FALSE' if self.is_postgres else '0'},
            approved_by TEXT,
            approval_timestamp {timestamp_type},
            metadata TEXT,
            created_at {timestamp_type} DEFAULT {default_timestamp},
            FOREIGN KEY (target_id) REFERENCES attribution_target(id)
        );
        """)

        # Actors table (lookup for all actor types: partners, campaigns, sales reps, etc.)
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS actors (
            id {pk},
            actor_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            name TEXT NOT NULL,
            metadata TEXT,
            created_at {timestamp_type} DEFAULT {default_timestamp},
            UNIQUE(actor_type, actor_id)
        );
        """)

        # Attribution Rule table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS attribution_rule (
            id {pk},
            name TEXT NOT NULL,
            model_type TEXT NOT NULL,
            config TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            created_at {timestamp_type} DEFAULT {default_timestamp},
            created_by TEXT,
            is_active {bool_type} DEFAULT {'TRUE' if self.is_postgres else '1'}
        );
        """)

        # Ledger Entry table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS ledger_entry (
            id {pk},
            target_id INTEGER NOT NULL,
            partner_id TEXT NOT NULL,
            attributed_value REAL NOT NULL,
            attribution_percentage REAL,
            split_percentage REAL NOT NULL,
            role TEXT NOT NULL,
            rule_id INTEGER NOT NULL,
            calculation_timestamp {timestamp_type} DEFAULT {default_timestamp},
            timestamp {timestamp_type} DEFAULT {default_timestamp},
            metadata TEXT,
            override_by TEXT,
            FOREIGN KEY (target_id) REFERENCES attribution_target(id),
            FOREIGN KEY (rule_id) REFERENCES attribution_rule(id)
        );
        """)

        # Measurement Workflow table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS measurement_workflow (
            id {pk},
            company_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            data_sources TEXT NOT NULL,
            conflict_resolution TEXT DEFAULT 'priority',
            fallback_strategy TEXT DEFAULT 'next_priority',
            applies_to TEXT,
            is_primary {bool_type} DEFAULT {'FALSE' if self.is_postgres else '0'},
            active {bool_type} DEFAULT {'TRUE' if self.is_postgres else '1'},
            created_at {timestamp_type} DEFAULT {default_timestamp},
            created_by TEXT
        );
        """)

        # Attribution Period table
        self.run_sql(f"""
        CREATE TABLE IF NOT EXISTS attribution_period (
            id {pk},
            organization_id TEXT NOT NULL,
            name TEXT NOT NULL,
            period_type TEXT NOT NULL,
            start_date {timestamp_type} NOT NULL,
            end_date {timestamp_type} NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            closed_at {timestamp_type},
            closed_by TEXT,
            locked_at {timestamp_type},
            locked_by TEXT,
            total_revenue REAL DEFAULT 0.0,
            total_deals INTEGER DEFAULT 0,
            total_partners INTEGER DEFAULT 0,
            created_at {timestamp_type} NOT NULL,
            created_by TEXT,
            notes TEXT
        );
        """)

        # Partners table (lookup/cache)
        self.run_sql("""
        CREATE TABLE IF NOT EXISTS partners (
            partner_id TEXT PRIMARY KEY,
            partner_name TEXT NOT NULL
        );
        """)

        # Run migrations for existing databases
        self._run_migrations()

        # Create indexes for performance
        self._create_indexes()

        logger.info("✅ Database schema initialized successfully")

    def _run_migrations(self):
        """Add missing columns to existing databases."""
        migrations = [
            # Attribution rule priority
            ("attribution_rule", "priority", "INTEGER DEFAULT 0"),
            # Attribution target revenue type and account fields
            ("attribution_target", "revenue_type", "TEXT"),
            ("attribution_target", "account_id", "TEXT"),
            ("attribution_target", "account_name", "TEXT"),
        ]

        for table, column, definition in migrations:
            try:
                if self.is_postgres:
                    self.run_sql(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
                else:
                    # SQLite: check if column exists first
                    cursor = self.adapter.execute(f"PRAGMA table_info({table})")
                    existing_cols = [row[1] for row in cursor.fetchall()]
                    if column not in existing_cols:
                        self.run_sql(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            except Exception as e:
                logger.warning(f"Migration skipped for {table}.{column}: {e}")

    def _create_indexes(self):
        """Create indexes for performance."""
        indexes = [
            # Partner touchpoint indexes
            "CREATE INDEX IF NOT EXISTS idx_touchpoint_target ON partner_touchpoint(target_id);",
            "CREATE INDEX IF NOT EXISTS idx_touchpoint_partner ON partner_touchpoint(partner_id);",
            # Universal touchpoint indexes
            "CREATE INDEX IF NOT EXISTS idx_univ_touchpoint_target ON touchpoint(target_id);",
            "CREATE INDEX IF NOT EXISTS idx_univ_touchpoint_actor ON touchpoint(actor_type, actor_id);",
            "CREATE INDEX IF NOT EXISTS idx_univ_touchpoint_type ON touchpoint(actor_type);",
            # Actors indexes
            "CREATE INDEX IF NOT EXISTS idx_actors_type ON actors(actor_type);",
            "CREATE INDEX IF NOT EXISTS idx_actors_lookup ON actors(actor_type, actor_id);",
            # Attribution target indexes
            "CREATE INDEX IF NOT EXISTS idx_target_revenue_type ON attribution_target(revenue_type);",
            "CREATE INDEX IF NOT EXISTS idx_target_account ON attribution_target(account_id);",
            # Ledger indexes
            "CREATE INDEX IF NOT EXISTS idx_ledger_target ON ledger_entry(target_id);",
            "CREATE INDEX IF NOT EXISTS idx_ledger_partner ON ledger_entry(partner_id);",
            # Period indexes
            "CREATE INDEX IF NOT EXISTS idx_period_org ON attribution_period(organization_id);",
            "CREATE INDEX IF NOT EXISTS idx_period_dates ON attribution_period(start_date, end_date);",
            # User/session indexes
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        ]

        for idx_sql in indexes:
            try:
                self.run_sql(idx_sql)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    def close(self):
        """Close database connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            logger.info("Database connection closed")
