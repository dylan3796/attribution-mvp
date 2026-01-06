"""
Login Page for Attribution Platform
====================================

Provides user authentication UI and session management for Streamlit.
"""

import streamlit as st
from auth import AuthManager, UserRole, create_default_organization_and_admin


def render_login_page(db_path: str):
    """Render login page."""
    st.set_page_config(page_title="Attribution Platform - Login", layout="centered")

    # Initialize auth manager
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = AuthManager(db_path)
        # Create default org and admin if needed
        create_default_organization_and_admin(db_path)

    # Custom CSS for login page
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px;
        font-weight: 600;
    }
    .stButton > button:hover {
        opacity: 0.9;
    }
    </style>
    """, unsafe_allow_html=True)

    # Center the content
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)

        # Logo/Title
        st.markdown("# 🎯 Attribution")
        st.markdown("### Partner Revenue Platform")
        st.caption("Sign in to continue")

        st.markdown("---")

        # Login form
        with st.form("login_form"):
            email = st.text_input(
                "Email",
                placeholder="you@company.com",
                key="login_email"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password"
            )

            submit = st.form_submit_button("Sign In")

            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    # Authenticate user
                    user = st.session_state.auth_manager.authenticate(email, password)

                    if user:
                        # Create session
                        session_id = st.session_state.auth_manager.create_session(user.id)

                        # Store in session state
                        st.session_state.authenticated = True
                        st.session_state.session_id = session_id
                        st.session_state.current_user = user

                        st.success(f"Welcome back, {user.name}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")

        st.markdown("</div>", unsafe_allow_html=True)

        # Help text
        st.markdown("---")
        st.caption("**Default credentials for demo:**")
        st.caption("Email: `admin@attribution.local`")
        st.caption("Password: `admin123`")
        st.caption("")
        st.caption("⚠️ Change default password in production")

        # Quick access button
        st.markdown("---")
        st.markdown("### 🚀 Quick Access")
        if st.button("Skip Login (Demo Mode)", type="secondary", use_container_width=True):
            # Create mock admin user for demo mode
            from auth import User, UserRole
            from datetime import datetime

            mock_user = User(
                id=1,
                email="demo@attribution.local",
                name="Demo User",
                role=UserRole.ADMIN,
                organization_id="ORG001",
                created_at=datetime.now()
            )

            st.session_state.authenticated = True
            st.session_state.session_id = "demo_session"
            st.session_state.current_user = mock_user

            st.success("✅ Logged in as Demo User (Admin)")
            st.rerun()


def check_authentication(db_path: str) -> bool:
    """
    Check if user is authenticated.
    Returns True if authenticated, False otherwise.
    """
    # Check if demo mode is active
    if st.session_state.get("session_id") == "demo_session":
        return st.session_state.get("authenticated", False)

    # Initialize auth manager if needed
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = AuthManager(db_path)

    # Check if user is authenticated
    if not st.session_state.get("authenticated", False):
        return False

    # Verify session is still valid
    session_id = st.session_state.get("session_id")
    if not session_id:
        return False

    user = st.session_state.auth_manager.get_session_user(session_id)
    if not user:
        # Session expired or invalid
        st.session_state.authenticated = False
        st.session_state.session_id = None
        st.session_state.current_user = None
        return False

    # Update current user in session state
    st.session_state.current_user = user

    return True


def logout():
    """Logout current user."""
    if "session_id" in st.session_state:
        st.session_state.auth_manager.invalidate_session(st.session_state.session_id)

    st.session_state.authenticated = False
    st.session_state.session_id = None
    st.session_state.current_user = None
    st.rerun()


def render_user_info_sidebar():
    """Render user info in sidebar."""
    if "current_user" in st.session_state and st.session_state.current_user:
        user = st.session_state.current_user

        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 Logged in as:")
            st.markdown(f"**{user.name}**")
            st.caption(f"{user.email}")
            st.caption(f"Role: {user.role.value.title()}")
            st.caption(f"Org: {user.organization_id}")

            if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
                logout()


def require_role(required_role: UserRole) -> bool:
    """
    Check if current user has required role.
    Shows error message if not.
    """
    if "current_user" not in st.session_state:
        st.error("Not authenticated")
        return False

    user = st.session_state.current_user

    if not AuthManager.has_permission(user, required_role):
        st.error(f"This feature requires {required_role.value} access or higher.")
        st.info(f"Your current role: {user.role.value}")
        return False

    return True


def can_user_manage_users() -> bool:
    """Check if current user can manage other users."""
    if "current_user" not in st.session_state:
        return False
    return AuthManager.can_manage_users(st.session_state.current_user)


def can_user_configure_rules() -> bool:
    """Check if current user can configure attribution rules."""
    if "current_user" not in st.session_state:
        return False
    return AuthManager.can_configure_rules(st.session_state.current_user)


def can_user_approve_touchpoints() -> bool:
    """Check if current user can approve touchpoints."""
    if "current_user" not in st.session_state:
        return False
    return AuthManager.can_approve_touchpoints(st.session_state.current_user)


def can_user_export_data() -> bool:
    """Check if current user can export data."""
    if "current_user" not in st.session_state:
        return False
    return AuthManager.can_export_data(st.session_state.current_user)


def get_current_organization_id() -> str:
    """Get current user's organization ID."""
    if "current_user" not in st.session_state:
        return "ORG001"  # Default
    return st.session_state.current_user.organization_id
