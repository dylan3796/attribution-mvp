"""
Salesforce Integration Tab
===========================

Allows users to:
1. Connect Salesforce via OAuth
2. Choose segment mode (1, 2, or 3)
3. Configure field mappings
4. Run initial sync
5. Manage ongoing sync schedule
"""

import streamlit as st
from datetime import datetime
from typing import Optional
import secrets

# Tab content (to be inserted into app_universal.py)

# ============================================================================
# TAB: SALESFORCE INTEGRATION
# ============================================================================

with tabs[9]:  # New tab after Ledger Explorer
    st.title("🔗 Salesforce Integration")
    st.caption("Connect your Salesforce org and configure data sync")

    # Initialize session state
    if "salesforce_connected" not in st.session_state:
        st.session_state.salesforce_connected = False

    if "salesforce_config" not in st.session_state:
        st.session_state.salesforce_config = {
            "segment_mode": None,
            "partner_field": "Partner__c",
            "role_field": None,
            "deal_reg_object": "Deal_Registration__c"
        }

    # ========================================================================
    # Step 1: Connect Salesforce
    # ========================================================================

    if not st.session_state.salesforce_connected:
        st.markdown("### Step 1: Connect Salesforce")

        st.info("""
        **Before connecting:**
        1. Create a Connected App in Salesforce
        2. Set OAuth redirect URI to: `http://localhost:8503/oauth/callback`
        3. Enable scopes: `api`, `refresh_token`
        4. Add your IP to the trusted IP ranges
        """)

        # OAuth configuration
        with st.form("salesforce_oauth"):
            client_id = st.text_input(
                "Consumer Key",
                placeholder="Paste your Connected App Consumer Key",
                help="Found in your Salesforce Connected App settings"
            )

            client_secret = st.text_input(
                "Consumer Secret",
                type="password",
                placeholder="Paste your Connected App Consumer Secret"
            )

            is_sandbox = st.checkbox("Connect to Sandbox", value=False)

            submit = st.form_submit_button("🔐 Connect Salesforce", type="primary", width='stretch')

            if submit:
                if client_id and client_secret:
                    # Generate OAuth URL
                    state = secrets.token_urlsafe(16)
                    base_url = "https://test.salesforce.com" if is_sandbox else "https://login.salesforce.com"

                    oauth_url = (
                        f"{base_url}/services/oauth2/authorize?"
                        f"response_type=code&"
                        f"client_id={client_id}&"
                        f"redirect_uri=http://localhost:8503/oauth/callback&"
                        f"state={state}"
                    )

                    st.success("✅ OAuth URL generated!")
                    st.markdown(f"**[Click here to authorize →]({oauth_url})**")

                    st.info("After authorizing, paste the authorization code below:")

                    # TODO: Handle OAuth callback
                    # For now, mock successful connection
                    if st.button("Simulate Successful Connection (Demo)", type="secondary"):
                        st.session_state.salesforce_connected = True
                        st.session_state.salesforce_instance_url = "https://yourinstance.salesforce.com"
                        st.rerun()

                else:
                    st.error("Please provide both Consumer Key and Consumer Secret")

    else:
        # Connected!
        st.success(f"✅ Connected to Salesforce: {st.session_state.salesforce_instance_url}")

        if st.button("🔌 Disconnect", type="secondary"):
            st.session_state.salesforce_connected = False
            st.rerun()

        st.markdown("---")

        # ====================================================================
        # Step 2: Choose Segment Mode
        # ====================================================================

        st.markdown("### Step 2: Choose Your Setup")

        segment_mode = st.radio(
            "How do you track partners today?",
            [
                "📌 **Segment 1**: Partners already tagged in Salesforce field",
                "🔍 **Segment 2**: Partners exist but not tagged (need inference)",
                "🚀 **Segment 3**: No partner tracking yet (greenfield)"
            ],
            help="This determines which data we'll sync from Salesforce"
        )

        # Extract segment number
        if "Segment 1" in segment_mode:
            st.session_state.salesforce_config["segment_mode"] = "segment_1"
        elif "Segment 2" in segment_mode:
            st.session_state.salesforce_config["segment_mode"] = "segment_2"
        else:
            st.session_state.salesforce_config["segment_mode"] = "segment_3"

        st.markdown("---")

        # ====================================================================
        # Step 3: Configure Field Mappings
        # ====================================================================

        st.markdown("### Step 3: Configure Field Mappings")

        mode = st.session_state.salesforce_config["segment_mode"]

        if mode == "segment_1":
            st.markdown("**Partner Field Configuration:**")

            partner_field = st.text_input(
                "Partner Field API Name",
                value=st.session_state.salesforce_config["partner_field"],
                placeholder="e.g., Partner__c, Reseller__c",
                help="The field on Opportunity that contains the partner"
            )

            role_field = st.text_input(
                "Partner Role Field (optional)",
                value=st.session_state.salesforce_config.get("role_field", ""),
                placeholder="e.g., Partner_Role__c",
                help="Optional field that specifies the partner's role"
            )

            st.session_state.salesforce_config["partner_field"] = partner_field
            st.session_state.salesforce_config["role_field"] = role_field if role_field else None

            st.info(f"""
            **We'll sync:**
            - Opportunities where `{partner_field}` is populated
            - Create attribution targets + touchpoints
            - 100% confidence (partner field = definitive)
            """)

        elif mode == "segment_2":
            st.markdown("**Multi-Source Configuration:**")

            st.markdown("**1. Partner Field (if available):**")
            has_partner_field = st.checkbox("I have a partner field (sometimes populated)", value=True)

            if has_partner_field:
                partner_field = st.text_input(
                    "Partner Field API Name",
                    value=st.session_state.salesforce_config["partner_field"],
                    placeholder="e.g., Partner__c"
                )
                st.session_state.salesforce_config["partner_field"] = partner_field
            else:
                st.session_state.salesforce_config["partner_field"] = None

            st.markdown("**2. Activity Tracking:**")
            sync_activities = st.checkbox("Sync Tasks & Events", value=True)
            sync_campaigns = st.checkbox("Sync Campaign Members", value=True)
            sync_contact_roles = st.checkbox("Sync Opportunity Contact Roles", value=True)

            st.session_state.salesforce_config["sync_activities"] = sync_activities
            st.session_state.salesforce_config["sync_campaigns"] = sync_campaigns
            st.session_state.salesforce_config["sync_contact_roles"] = sync_contact_roles

            st.info("""
            **We'll sync:**
            - Partner field (when populated) = High confidence
            - Activities, campaigns, contact roles = Inference engine
            - Confidence scoring based on proximity + account match
            """)

        else:  # segment_3
            st.markdown("**Deal Registration Configuration:**")

            deal_reg_object = st.text_input(
                "Deal Registration Object API Name",
                value=st.session_state.salesforce_config["deal_reg_object"],
                placeholder="e.g., Deal_Registration__c",
                help="Custom object where partners submit deal registrations"
            )

            st.session_state.salesforce_config["deal_reg_object"] = deal_reg_object

            st.markdown("**Deal Registration Fields:**")
            col1, col2 = st.columns(2)

            with col1:
                st.text_input("Partner Field", value="Partner__c", disabled=True)
                st.text_input("Status Field", value="Status__c", disabled=True)
                st.text_input("Submitted Date", value="Submitted_Date__c", disabled=True)

            with col2:
                st.text_input("Opportunity Field", value="Opportunity__c", disabled=True)
                st.text_input("Approved By", value="Approved_By__c", disabled=True)
                st.text_input("Approved Date", value="Approved_Date__c", disabled=True)

            st.info("""
            **We'll sync:**
            - Deal registrations (approval workflow)
            - Opportunities (for context)
            - Expiry management (90-day default)
            """)

        st.markdown("---")

        # ====================================================================
        # Step 4: Run Initial Sync
        # ====================================================================

        st.markdown("### Step 4: Run Initial Sync")

        col1, col2 = st.columns([2, 1])

        with col1:
            sync_period = st.selectbox(
                "Sync data from:",
                ["Last 7 days", "Last 30 days", "Last 90 days", "Last year", "All time"],
                index=2
            )

        with col2:
            st.markdown("")
            st.markdown("")

            if st.button("🚀 Start Sync", type="primary", width='stretch'):
                with st.spinner("Syncing data from Salesforce..."):
                    # TODO: Call salesforce_connector.py
                    # For now, simulate sync
                    import time
                    time.sleep(2)

                    st.success("✅ Sync completed!")
                    st.balloons()

                    # Mock sync results
                    st.session_state.sync_results = {
                        "targets": 145,
                        "touchpoints": 432,
                        "partners": 28
                    }

        # Show sync results
        if "sync_results" in st.session_state:
            st.markdown("---")
            st.markdown("### Sync Results")

            results = st.session_state.sync_results

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Opportunities Synced", f"{results['targets']:,}")

            with col2:
                st.metric("Touchpoints Created", f"{results['touchpoints']:,}")

            with col3:
                st.metric("Partners Identified", f"{results['partners']:,}")

        st.markdown("---")

        # ====================================================================
        # Step 5: Ongoing Sync Schedule
        # ====================================================================

        st.markdown("### Step 5: Ongoing Sync")

        sync_frequency = st.select_slider(
            "Auto-sync frequency",
            options=["Manual only", "Every hour", "Every 15 minutes", "Real-time (webhooks)"],
            value="Every hour"
        )

        if sync_frequency != "Manual only":
            st.info(f"✅ Auto-sync enabled: {sync_frequency}")
        else:
            st.warning("⚠️ Auto-sync disabled - you'll need to manually sync")

        st.markdown("---")

        # ====================================================================
        # Partner Invitation
        # ====================================================================

        st.markdown("### 📨 Invite Partners to Portal")

        with st.expander("Invite partners to view their attribution"):
            st.markdown("""
            Give your partners real-time visibility into their attributed revenue.

            **They'll be able to:**
            - View their ledger across all deals
            - See split percentages and methodology
            - Submit self-reported activities
            - Export statements for their records
            """)

            partner_to_invite = st.selectbox(
                "Select partner to invite",
                options=list(st.session_state.partners.keys()),
                format_func=lambda pid: f"{st.session_state.partners[pid]} ({pid})"
            )

            partner_email = st.text_input(
                "Partner email",
                placeholder="partner@company.com"
            )

            if st.button("📧 Send Invitation", type="primary"):
                if partner_email:
                    # TODO: Generate invitation link and send email
                    st.success(f"✅ Invitation sent to {partner_email}")

                    # Show preview
                    with st.expander("Email Preview"):
                        st.markdown(f"""
                        **Subject:** You've been invited to view your attributed revenue

                        Hi {st.session_state.partners[partner_to_invite]},

                        You've been invited to view your real-time attributed revenue!

                        Click here to create your account: [Partner Portal]

                        - View your ledger
                        - Track performance
                        - Submit activities

                        Thanks!
                        """)
                else:
                    st.error("Please enter partner email")
