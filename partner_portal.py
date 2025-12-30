"""
Partner Portal - Self-Service Attribution Dashboard
===================================================

Allows partners to:
1. View their attributed revenue across all customers
2. See deal-level breakdowns
3. Submit self-reported activities
4. Dispute incorrect attributions

This enables the two-sided platform strategy.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
import secrets
import warnings

# Suppress deprecation warnings
warnings.filterwarnings('ignore', message='.*Plotly configuration.*')
warnings.filterwarnings('ignore', message='.*label.*got an empty value.*')

from models_new import LedgerEntry, AttributionTarget, PartnerTouchpoint, TouchpointType
from dashboards import create_revenue_over_time_chart


# ============================================================================
# Partner Authentication
# ============================================================================

class PartnerAuth:
    """Simple email + password authentication for partners."""

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt."""
        if not salt:
            salt = secrets.token_hex(16)

        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return pwd_hash.hex(), salt

    @staticmethod
    def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
        """Verify password against hash."""
        new_hash, _ = PartnerAuth.hash_password(password, salt)
        return new_hash == pwd_hash

    @staticmethod
    def create_partner_account(
        partner_id: str,
        email: str,
        password: str,
        partner_name: str,
        company_id: str
    ) -> Dict:
        """Create new partner account."""
        pwd_hash, salt = PartnerAuth.hash_password(password)

        return {
            "partner_id": partner_id,
            "email": email,
            "password_hash": pwd_hash,
            "salt": salt,
            "partner_name": partner_name,
            "company_id": company_id,
            "created_at": datetime.now(),
            "last_login": None,
            "is_active": True
        }


# ============================================================================
# Partner Invitation Flow
# ============================================================================

def send_partner_invitation(
    partner_id: str,
    partner_email: str,
    partner_name: str,
    company_name: str,
    invitation_link: str
) -> str:
    """
    Generate invitation email for partner.

    Returns: Email HTML template
    """
    email_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 10px; margin-top: 20px; }}
            .button {{ background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 You've Been Invited!</h1>
            </div>

            <div class="content">
                <h2>Hi {partner_name},</h2>

                <p><strong>{company_name}</strong> has invited you to view your attributed revenue in real-time.</p>

                <p>You'll be able to:</p>
                <ul>
                    <li>✅ See your attributed revenue across all deals</li>
                    <li>✅ View deal-level breakdowns and split percentages</li>
                    <li>✅ Track your performance over time</li>
                    <li>✅ Submit activities to ensure proper attribution</li>
                </ul>

                <p><strong>No more spreadsheets. No more waiting for quarterly statements.</strong></p>
                <p>Everything is transparent and updated in real-time.</p>

                <a href="{invitation_link}" class="button">View Your Dashboard →</a>

                <p style="margin-top: 30px; font-size: 14px; color: #6b7280;">
                    This link will expire in 7 days. Click above to create your account.
                </p>
            </div>

            <div class="footer">
                <p>Powered by Attribution Platform</p>
                <p>If you have questions, contact {company_name} directly.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return email_html


# ============================================================================
# Partner Dashboard UI
# ============================================================================

def render_partner_login():
    """Render partner login page."""
    st.set_page_config(page_title="Partner Portal", layout="wide")

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
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-container'>", unsafe_allow_html=True)

    st.title("🤝 Partner Portal")
    st.caption("View your attributed revenue and performance")

    # Login form
    with st.form("partner_login"):
        email = st.text_input("Email", placeholder="partner@company.com")
        password = st.text_input("Password", type="password")

        submit = st.form_submit_button("Sign In", type="primary", width='stretch')

        if submit:
            # Validate credentials
            if email and password:
                # TODO: Check against partner_accounts table
                # For now, mock authentication
                st.session_state.partner_authenticated = True
                st.session_state.partner_id = "P001"
                st.session_state.partner_name = "Accenture"
                st.session_state.partner_email = email
                st.rerun()
            else:
                st.error("Please enter email and password")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**New partner?** Check your email for an invitation link.")


def render_partner_dashboard(
    partner_id: str,
    partner_name: str,
    ledger: List[LedgerEntry],
    targets: List[AttributionTarget]
):
    """Render main partner dashboard."""

    st.set_page_config(page_title=f"{partner_name} - Partner Portal", layout="wide")

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"👋 Welcome, {partner_name}")
        st.caption("Your attributed revenue across all customers")

    with col2:
        if st.button("🚪 Logout", width='stretch'):
            st.session_state.partner_authenticated = False
            st.rerun()

    st.markdown("---")

    # Filter ledger to this partner
    partner_ledger = [e for e in ledger if e.partner_id == partner_id]

    if not partner_ledger:
        st.info("📭 No attributed revenue yet. Check back soon!")
        return

    # Performance metrics
    total_revenue = sum(e.attributed_value for e in partner_ledger)
    deal_count = len(set(e.target_id for e in partner_ledger))
    avg_attribution = total_revenue / deal_count if deal_count > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Attributed Revenue",
            f"${total_revenue:,.0f}",
            help="Total revenue attributed to you across all deals"
        )

    with col2:
        st.metric(
            "Deals Influenced",
            f"{deal_count}",
            help="Number of deals you were credited on"
        )

    with col3:
        st.metric(
            "Average Attribution",
            f"${avg_attribution:,.0f}",
            help="Average attributed value per deal"
        )

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Performance Overview",
        "💰 Deal Breakdown",
        "📝 Submit Activity"
    ])

    # Tab 1: Performance Overview
    with tab1:
        st.markdown("### Revenue Over Time")

        # Group by month
        ledger_df = pd.DataFrame([
            {
                "date": e.calculation_timestamp,
                "revenue": e.attributed_value,
                "split": e.split_percentage * 100
            }
            for e in partner_ledger
        ])

        ledger_df["month"] = pd.to_datetime(ledger_df["date"]).dt.to_period("M")
        monthly_revenue = ledger_df.groupby("month")["revenue"].sum().reset_index()
        monthly_revenue["month"] = monthly_revenue["month"].astype(str)

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly_revenue["month"],
            y=monthly_revenue["revenue"],
            marker_color='#667eea',
            name="Revenue"
        ))

        fig.update_layout(
            title="Monthly Attributed Revenue",
            xaxis_title="Month",
            yaxis_title="Revenue ($)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Attribution distribution
        st.markdown("### Attribution Split Distribution")

        split_distribution = ledger_df["split"].value_counts().reset_index()
        split_distribution.columns = ["Split %", "Count"]

        fig2 = go.Figure(data=[go.Pie(
            labels=split_distribution["Split %"],
            values=split_distribution["Count"],
            hole=0.4
        )])

        fig2.update_layout(
            title="How Your Credit is Split",
            height=400
        )

        st.plotly_chart(fig2, use_container_width=True)

    # Tab 2: Deal Breakdown
    with tab2:
        st.markdown("### Deal-Level Attribution")

        # Build deal table
        deal_data = []
        for entry in partner_ledger:
            target = next((t for t in targets if t.id == entry.target_id), None)
            if not target:
                continue

            deal_data.append({
                "Deal": target.name or target.external_id,
                "Deal Value": f"${target.value:,.0f}",
                "Your Attribution": f"${entry.attributed_value:,.0f}",
                "Split %": f"{entry.split_percentage * 100:.1f}%",
                "Role": entry.metadata.get("role", "Unknown"),
                "Date": entry.calculation_timestamp.strftime("%Y-%m-%d")
            })

        if deal_data:
            deal_df = pd.DataFrame(deal_data)
            st.dataframe(deal_df, use_container_width=True, hide_index=True)

            # Export
            csv = deal_df.to_csv(index=False)
            st.download_button(
                "📥 Export CSV",
                csv,
                "partner_attribution.csv",
                "text/csv",
                width='stretch'
            )
        else:
            st.info("No deal details available")

    # Tab 3: Submit Activity
    with tab3:
        st.markdown("### Report Your Activity")
        st.caption("Help us attribute deals accurately by logging your involvement")

        with st.form("submit_activity"):
            st.markdown("**Activity Details:**")

            account_name = st.text_input(
                "Account/Customer Name",
                placeholder="e.g., Acme Corp"
            )

            activity_type = st.selectbox(
                "Activity Type",
                ["Meeting", "Demo", "Technical Workshop", "Referral", "Introduction", "Other"]
            )

            activity_date = st.date_input(
                "Activity Date",
                value=datetime.now()
            )

            description = st.text_area(
                "Description",
                placeholder="Briefly describe what you did...",
                height=100
            )

            submit = st.form_submit_button("Submit Activity", type="primary", width='stretch')

            if submit:
                if account_name and description:
                    # Create touchpoint for approval
                    new_touchpoint = PartnerTouchpoint(
                        id=0,
                        partner_id=partner_id,
                        target_id=0,  # Will be linked by company
                        touchpoint_type=TouchpointType.PARTNER_SELF_REPORTED,
                        role="Influence",
                        weight=1.0,
                        timestamp=datetime.combine(activity_date, datetime.min.time()),
                        source="partner_portal_reporting",
                        source_confidence=0.8,
                        requires_approval=True,
                        metadata={
                            "account_name": account_name,
                            "activity_type": activity_type,
                            "description": description,
                            "submitted_by": partner_name
                        }
                    )

                    # TODO: Save to pending_touchpoints table
                    st.success("✅ Activity submitted! Your customer will review and approve.")
                    st.balloons()
                else:
                    st.error("Please fill in all required fields")


# ============================================================================
# Partner Portal App (Separate from Main App)
# ============================================================================

def main():
    """Main partner portal app."""

    # Initialize session state
    if "partner_authenticated" not in st.session_state:
        st.session_state.partner_authenticated = False

    # Show login or dashboard
    if not st.session_state.partner_authenticated:
        render_partner_login()
    else:
        # Load partner data
        partner_id = st.session_state.partner_id
        partner_name = st.session_state.partner_name

        # TODO: Load from database
        # Mock data for now
        ledger = st.session_state.get("ledger", [])
        targets = st.session_state.get("targets", [])

        render_partner_dashboard(partner_id, partner_name, ledger, targets)


if __name__ == "__main__":
    main()
