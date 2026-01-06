"""
Database Connection Manager
===========================

Handles connections to both SQLite (local development) and PostgreSQL (production).
Automatically detects which database to use based on environment.
"""

import os
import sqlite3
from typing import Optional
import streamlit as st


def get_database_url() -> str:
    """
    Get database URL from environment or Streamlit secrets.

    Priority:
    1. Streamlit secrets (production)
    2. Environment variable (local with .env)
    3. SQLite fallback (local development)
    """
    # Try Streamlit secrets first (production)
    try:
        if hasattr(st, 'secrets') and 'database' in st.secrets:
            db_url = st.secrets['database'].get('url')
            if db_url:
                print(f"✅ Using PostgreSQL from Streamlit secrets")
                return db_url
    except Exception as e:
        print(f"ℹ️ No database secrets found: {e}")

    # Try environment variable
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print(f"✅ Using PostgreSQL from DATABASE_URL")
        return db_url

    # Fallback to SQLite
    print(f"ℹ️ Using SQLite (local development mode)")
    return "sqlite:///attribution.db"


def is_postgres() -> bool:
    """Check if we're using PostgreSQL."""
    db_url = get_database_url()
    return db_url.startswith('postgresql://') or db_url.startswith('postgres://')


def get_connection():
    """
    Get database connection based on database type.

    Returns:
        For SQLite: sqlite3.Connection
        For PostgreSQL: psycopg2.connection
    """
    db_url = get_database_url()

    if db_url.startswith('sqlite'):
        # SQLite connection
        db_path = db_url.replace('sqlite:///', '')
        return sqlite3.connect(db_path, check_same_thread=False)
    else:
        # PostgreSQL connection
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Parse the URL
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


class DatabaseAdapter:
    """
    Adapter to provide consistent interface for both SQLite and PostgreSQL.
    Handles SQL syntax differences between the two databases.
    """

    def __init__(self, conn):
        self.conn = conn
        self.is_postgres = is_postgres()

    def execute(self, sql: str, params: tuple = ()):
        """Execute SQL with automatic parameter placeholder conversion."""
        # Convert ? placeholders to %s for PostgreSQL
        if self.is_postgres and '?' in sql:
            # Count placeholders
            placeholder_count = sql.count('?')
            # Replace with %s
            sql = sql.replace('?', '%s')

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self):
        """Commit transaction."""
        self.conn.commit()

    def rollback(self):
        """Rollback transaction."""
        self.conn.rollback()

    def close(self):
        """Close connection."""
        self.conn.close()

    def get_autoincrement_syntax(self) -> str:
        """Get the correct AUTO_INCREMENT syntax for the database."""
        if self.is_postgres:
            return "SERIAL"
        else:
            return "INTEGER PRIMARY KEY AUTOINCREMENT"

    def get_last_insert_id(self, cursor) -> int:
        """Get the last inserted ID."""
        if self.is_postgres:
            # PostgreSQL uses RETURNING
            return cursor.fetchone()[0]
        else:
            # SQLite uses lastrowid
            return cursor.lastrowid

    def get_datetime_type(self) -> str:
        """Get the correct datetime type for the database."""
        if self.is_postgres:
            return "TIMESTAMP"
        else:
            return "TEXT"

    def get_boolean_type(self) -> str:
        """Get the correct boolean type for the database."""
        if self.is_postgres:
            return "BOOLEAN"
        else:
            return "INTEGER"
