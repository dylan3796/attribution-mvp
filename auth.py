"""
Authentication and User Management System
==========================================

Provides user authentication, session management, and role-based access control
for the attribution platform.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class UserRole(str, Enum):
    """User roles for access control."""
    ADMIN = "admin"            # Full access, can manage users
    MANAGER = "manager"        # Can configure rules and view all data
    ANALYST = "analyst"        # Can view dashboards and export data
    PARTNER_OPS = "partner_ops"  # Can manage partner relationships and approvals
    VIEWER = "viewer"          # Read-only access to dashboards


@dataclass
class User:
    """User account."""
    id: int
    email: str
    name: str
    role: UserRole
    organization_id: str
    password_hash: str
    salt: str
    is_active: bool = True
    created_at: datetime = None
    last_login: Optional[datetime] = None


class AuthManager:
    """Manages user authentication and sessions."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create authentication tables."""
        cursor = self.conn.cursor()

        # Organizations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            )
        """)

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")

        self.conn.commit()

    # ========================================================================
    # Password Hashing
    # ========================================================================

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with PBKDF2 and salt."""
        if not salt:
            salt = secrets.token_hex(32)

        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return pwd_hash.hex(), salt

    @staticmethod
    def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
        """Verify password against hash."""
        new_hash, _ = AuthManager.hash_password(password, salt)
        return secrets.compare_digest(new_hash, pwd_hash)

    # ========================================================================
    # Organization Management
    # ========================================================================

    def create_organization(self, org_id: str, name: str) -> None:
        """Create a new organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO organizations (id, name, created_at)
            VALUES (?, ?, ?)
        """, (org_id, name, datetime.now().isoformat()))
        self.conn.commit()

    def get_organization(self, org_id: str) -> Optional[Dict]:
        """Get organization by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE id = ?", (org_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row['id'],
            "name": row['name'],
            "created_at": datetime.fromisoformat(row['created_at']),
            "is_active": bool(row['is_active'])
        }

    # ========================================================================
    # User Management
    # ========================================================================

    def create_user(
        self,
        email: str,
        name: str,
        password: str,
        role: UserRole,
        organization_id: str
    ) -> int:
        """Create a new user account."""
        pwd_hash, salt = self.hash_password(password)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO users (
                email, name, role, organization_id,
                password_hash, salt, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            email.lower(),
            name,
            role.value,
            organization_id,
            pwd_hash,
            salt,
            datetime.now().isoformat()
        ))
        self.conn.commit()

        return cursor.lastrowid

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()

        if not row:
            return None

        return User(
            id=row['id'],
            email=row['email'],
            name=row['name'],
            role=UserRole(row['role']),
            organization_id=row['organization_id'],
            password_hash=row['password_hash'],
            salt=row['salt'],
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at']),
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
        )

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return User(
            id=row['id'],
            email=row['email'],
            name=row['name'],
            role=UserRole(row['role']),
            organization_id=row['organization_id'],
            password_hash=row['password_hash'],
            salt=row['salt'],
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at']),
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
        )

    def get_users_by_organization(self, organization_id: str) -> List[User]:
        """Get all users in an organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM users
            WHERE organization_id = ?
            ORDER BY created_at DESC
        """, (organization_id,))
        rows = cursor.fetchall()

        users = []
        for row in rows:
            users.append(User(
                id=row['id'],
                email=row['email'],
                name=row['name'],
                role=UserRole(row['role']),
                organization_id=row['organization_id'],
                password_hash=row['password_hash'],
                salt=row['salt'],
                is_active=bool(row['is_active']),
                created_at=datetime.fromisoformat(row['created_at']),
                last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
            ))

        return users

    def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET last_login = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), user_id))
        self.conn.commit()

    def change_password(self, user_id: int, new_password: str) -> None:
        """Change user password."""
        pwd_hash, salt = self.hash_password(new_password)

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET password_hash = ?, salt = ?
            WHERE id = ?
        """, (pwd_hash, salt, user_id))
        self.conn.commit()

    def deactivate_user(self, user_id: int) -> None:
        """Deactivate a user account."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET is_active = 0
            WHERE id = ?
        """, (user_id,))
        self.conn.commit()

    def activate_user(self, user_id: int) -> None:
        """Activate a user account."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET is_active = 1
            WHERE id = ?
        """, (user_id,))
        self.conn.commit()

    # ========================================================================
    # Authentication
    # ========================================================================

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(email)

        if not user:
            return None

        if not user.is_active:
            return None

        if not self.verify_password(password, user.password_hash, user.salt):
            return None

        # Update last login
        self.update_last_login(user.id)

        return user

    # ========================================================================
    # Session Management
    # ========================================================================

    def create_session(self, user_id: int, duration_hours: int = 24) -> str:
        """Create a new session for a user."""
        session_id = secrets.token_urlsafe(32)
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=duration_hours)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_id, created_at.isoformat(), expires_at.isoformat()))
        self.conn.commit()

        return session_id

    def get_session_user(self, session_id: str) -> Optional[User]:
        """Get user from session ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions
            WHERE session_id = ? AND is_active = 1
        """, (session_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Check if session expired
        expires_at = datetime.fromisoformat(row['expires_at'])
        if expires_at < datetime.now():
            self.invalidate_session(session_id)
            return None

        # Get user
        return self.get_user_by_id(row['user_id'])

    def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET is_active = 0
            WHERE session_id = ?
        """, (session_id,))
        self.conn.commit()

    def invalidate_all_user_sessions(self, user_id: int) -> None:
        """Invalidate all sessions for a user."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET is_active = 0
            WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()

    # ========================================================================
    # Access Control
    # ========================================================================

    @staticmethod
    def has_permission(user: User, required_role: UserRole) -> bool:
        """Check if user has required role or higher."""
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.ANALYST: 2,
            UserRole.PARTNER_OPS: 3,
            UserRole.MANAGER: 4,
            UserRole.ADMIN: 5
        }

        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level

    @staticmethod
    def can_manage_users(user: User) -> bool:
        """Check if user can manage other users."""
        return user.role == UserRole.ADMIN

    @staticmethod
    def can_configure_rules(user: User) -> bool:
        """Check if user can configure attribution rules."""
        return user.role in [UserRole.ADMIN, UserRole.MANAGER]

    @staticmethod
    def can_approve_touchpoints(user: User) -> bool:
        """Check if user can approve partner touchpoints."""
        return user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.PARTNER_OPS]

    @staticmethod
    def can_export_data(user: User) -> bool:
        """Check if user can export data."""
        return user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST]

    def close(self):
        """Close database connection."""
        self.conn.close()


def create_default_organization_and_admin(db_path: str):
    """Create default organization and admin user for initial setup."""
    import streamlit as st

    auth = AuthManager(db_path)

    # Create default organization
    org_id = "ORG001"
    org_name = "Default Organization"

    # Check if Streamlit secrets has custom org name
    try:
        if hasattr(st, 'secrets') and 'organization' in st.secrets:
            org_name = st.secrets['organization'].get('name', org_name)
    except Exception:
        pass

    try:
        auth.create_organization(org_id, org_name)
    except sqlite3.IntegrityError:
        # Organization already exists
        pass

    # Get admin credentials from Streamlit secrets or use defaults
    admin_email = "admin@attribution.local"
    admin_password = "admin123"
    admin_name = "System Administrator"

    try:
        if hasattr(st, 'secrets') and 'admin' in st.secrets:
            admin_email = st.secrets['admin'].get('email', admin_email)
            admin_password = st.secrets['admin'].get('password', admin_password)
            admin_name = st.secrets['admin'].get('name', admin_name)
            print(f"✅ Using admin credentials from Streamlit secrets: {admin_email}")
    except Exception as e:
        print(f"ℹ️ No secrets found, using default credentials: {e}")

    # Create admin user
    try:
        auth.create_user(
            email=admin_email,
            name=admin_name,
            password=admin_password,
            role=UserRole.ADMIN,
            organization_id=org_id
        )
        if admin_email == "admin@attribution.local":
            print("✅ Default admin created: admin@attribution.local / admin123")
        else:
            print(f"✅ Admin created from secrets: {admin_email}")
    except sqlite3.IntegrityError:
        # User already exists
        pass

    auth.close()
