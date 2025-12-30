"""
Salesforce OAuth Connector & Data Sync
======================================

Handles OAuth authentication, data sync for:
- Opportunities → AttributionTarget
- Partner fields → PartnerTouchpoint
- Activities, Campaign Members, Contact Roles → PartnerTouchpoint
- Deal Registrations → PartnerTouchpoint

Supports all 3 customer segments:
1. Partner field already populated
2. Partners tagged indirectly (activities/campaigns)
3. No partner info (greenfield with deal reg)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from simple_salesforce import Salesforce, SalesforceLogin
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
import requests

from models_new import (
    AttributionTarget, PartnerTouchpoint,
    TargetType, TouchpointType, DataSource
)


# ============================================================================
# OAuth Configuration
# ============================================================================

class SalesforceOAuthConfig:
    """OAuth configuration for Salesforce Connected App."""

    def __init__(self):
        self.client_id = os.getenv("SALESFORCE_CLIENT_ID")
        self.client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SALESFORCE_REDIRECT_URI", "http://localhost:8503/oauth/callback")
        self.authorize_url = "https://login.salesforce.com/services/oauth2/authorize"
        self.token_url = "https://login.salesforce.com/services/oauth2/token"

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "api refresh_token"
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.authorize_url}?{query_string}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code": code
        }

        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token."""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token
        }

        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()


# ============================================================================
# Salesforce Client
# ============================================================================

class SalesforceClient:
    """
    Salesforce API client with data sync capabilities.

    Supports 3 sync modes:
    1. Partner Field Mode: Sync Opportunity.Partner__c
    2. Touchpoint Mode: Sync Activities, Campaign Members, Contact Roles
    3. Hybrid Mode: Both
    """

    def __init__(self, access_token: str, instance_url: str):
        """Initialize Salesforce client with OAuth credentials."""
        self.sf = Salesforce(
            instance_url=instance_url,
            session_id=access_token,
            version="58.0"
        )
        self.instance_url = instance_url

    # ========================================================================
    # Segment 1: Partner Field Sync
    # ========================================================================

    def sync_opportunities_with_partner_field(
        self,
        partner_field: str = "Partner__c",
        role_field: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Tuple[List[AttributionTarget], List[PartnerTouchpoint]]:
        """
        Sync opportunities where partner field is populated.

        Args:
            partner_field: API name of partner field (e.g., "Partner__c")
            role_field: Optional field for partner role (e.g., "Partner_Role__c")
            since: Only sync opportunities modified since this date

        Returns:
            (targets, touchpoints) tuple
        """
        # Build SOQL query
        fields = [
            "Id", "Name", "Amount", "StageName", "CloseDate",
            "CreatedDate", "AccountId", partner_field
        ]
        if role_field:
            fields.append(role_field)

        where_clause = f"{partner_field} != null"
        if since:
            where_clause += f" AND LastModifiedDate >= {since.isoformat()}"

        query = f"""
            SELECT {', '.join(fields)}
            FROM Opportunity
            WHERE {where_clause}
        """

        results = self.sf.query_all(query)

        targets = []
        touchpoints = []

        for opp in results["records"]:
            # Create target
            target = AttributionTarget(
                id=0,  # Will be assigned by DB
                type=TargetType.OPPORTUNITY,
                external_id=opp["Id"],
                name=opp["Name"],
                value=opp.get("Amount", 0) or 0,
                timestamp=datetime.fromisoformat(opp["CloseDate"]),
                metadata={
                    "stage": opp.get("StageName"),
                    "account_id": opp.get("AccountId"),
                    "created_date": opp.get("CreatedDate"),
                    "salesforce_url": f"{self.instance_url}/{opp['Id']}"
                }
            )
            targets.append(target)

            # Create touchpoint from partner field
            partner_id = opp[partner_field]
            role = opp.get(role_field, "Partner") if role_field else "Partner"

            touchpoint = PartnerTouchpoint(
                id=0,
                partner_id=partner_id,
                target_id=0,  # Will be linked after target is created
                touchpoint_type=TouchpointType.CRM_PARTNER_FIELD,
                role=role,
                weight=1.0,
                timestamp=datetime.fromisoformat(opp["CreatedDate"]),
                source=DataSource.CRM_OPPORTUNITY_FIELD,
                source_id=opp["Id"],
                source_confidence=1.0,  # Partner field = definitive
                metadata={
                    "field_name": partner_field,
                    "opportunity_name": opp["Name"]
                }
            )
            touchpoints.append(touchpoint)

        return targets, touchpoints

    # ========================================================================
    # Segment 2: Activity & Campaign Sync (Inference)
    # ========================================================================

    def sync_activities_for_opportunities(
        self,
        opportunity_ids: Optional[List[str]] = None,
        since: Optional[datetime] = None
    ) -> List[PartnerTouchpoint]:
        """
        Sync activities (Tasks, Events) related to opportunities.

        This requires inference: Activity.WhoId (Contact) → Contact.Account → Opportunity
        """
        # Build query
        where_clauses = []
        if opportunity_ids:
            where_clauses.append(f"WhatId IN {self._format_id_list(opportunity_ids)}")
        if since:
            where_clauses.append(f"LastModifiedDate >= {since.isoformat()}")

        where_clause = " AND ".join(where_clauses) if where_clauses else "WhatId != null"

        # Query Tasks
        task_query = f"""
            SELECT Id, Subject, WhoId, WhatId, ActivityDate, CreatedDate
            FROM Task
            WHERE {where_clause}
        """

        # Query Events
        event_query = f"""
            SELECT Id, Subject, WhoId, WhatId, StartDateTime, CreatedDate
            FROM Event
            WHERE {where_clause}
        """

        tasks = self.sf.query_all(task_query)["records"]
        events = self.sf.query_all(event_query)["records"]

        touchpoints = []

        # Process tasks
        for task in tasks:
            touchpoint = self._activity_to_touchpoint(task, "Task")
            if touchpoint:
                touchpoints.append(touchpoint)

        # Process events
        for event in events:
            touchpoint = self._activity_to_touchpoint(event, "Event")
            if touchpoint:
                touchpoints.append(touchpoint)

        return touchpoints

    def sync_campaign_members(
        self,
        campaign_ids: Optional[List[str]] = None
    ) -> List[PartnerTouchpoint]:
        """Sync campaign members (partner marketing activities)."""
        where_clause = "ContactId != null"
        if campaign_ids:
            where_clause += f" AND CampaignId IN {self._format_id_list(campaign_ids)}"

        query = f"""
            SELECT Id, CampaignId, ContactId, Status, CreatedDate
            FROM CampaignMember
            WHERE {where_clause}
        """

        results = self.sf.query_all(query)
        touchpoints = []

        for member in results["records"]:
            # Need to map Contact → Account → Partner
            # For now, create touchpoint with contact as partner_id
            touchpoint = PartnerTouchpoint(
                id=0,
                partner_id=member["ContactId"],  # TODO: Map to actual partner
                target_id=0,
                touchpoint_type=TouchpointType.ACTIVITY,
                role="Influence",
                weight=2.0,  # Campaign engagement = moderate weight
                timestamp=datetime.fromisoformat(member["CreatedDate"]),
                source=DataSource.TOUCHPOINT_TRACKING,
                source_id=member["Id"],
                source_confidence=0.7,  # Campaign member = indirect evidence
                metadata={
                    "campaign_id": member["CampaignId"],
                    "status": member.get("Status")
                }
            )
            touchpoints.append(touchpoint)

        return touchpoints

    def sync_contact_roles(
        self,
        opportunity_ids: Optional[List[str]] = None
    ) -> List[PartnerTouchpoint]:
        """Sync Opportunity Contact Roles."""
        where_clause = "OpportunityId != null"
        if opportunity_ids:
            where_clause += f" AND OpportunityId IN {self._format_id_list(opportunity_ids)}"

        query = f"""
            SELECT Id, OpportunityId, ContactId, Role, CreatedDate
            FROM OpportunityContactRole
            WHERE {where_clause}
        """

        results = self.sf.query_all(query)
        touchpoints = []

        for role in results["records"]:
            touchpoint = PartnerTouchpoint(
                id=0,
                partner_id=role["ContactId"],  # TODO: Map to partner
                target_id=0,
                touchpoint_type=TouchpointType.CONTACT_ROLE,
                role=role.get("Role", "Unknown"),
                weight=3.0,  # Contact role = strong signal
                timestamp=datetime.fromisoformat(role["CreatedDate"]),
                source=DataSource.TOUCHPOINT_TRACKING,
                source_id=role["Id"],
                source_confidence=0.8,
                metadata={
                    "opportunity_id": role["OpportunityId"]
                }
            )
            touchpoints.append(touchpoint)

        return touchpoints

    # ========================================================================
    # Segment 3: Deal Registration Sync
    # ========================================================================

    def sync_deal_registrations(
        self,
        deal_reg_object: str = "Deal_Registration__c",
        since: Optional[datetime] = None
    ) -> List[PartnerTouchpoint]:
        """
        Sync deal registrations from custom object.

        Args:
            deal_reg_object: API name of deal reg custom object
            since: Only sync records created/modified since this date
        """
        where_clause = "Partner__c != null"
        if since:
            where_clause += f" AND LastModifiedDate >= {since.isoformat()}"

        query = f"""
            SELECT Id, Name, Partner__c, Opportunity__c,
                   Status__c, Submitted_Date__c, Approved_Date__c,
                   Approved_By__c, Estimated_Value__c
            FROM {deal_reg_object}
            WHERE {where_clause}
        """

        results = self.sf.query_all(query)
        touchpoints = []

        for reg in results["records"]:
            touchpoint = PartnerTouchpoint(
                id=0,
                partner_id=reg["Partner__c"],
                target_id=0,
                touchpoint_type=TouchpointType.DEAL_REGISTRATION,
                role="Referral",
                weight=1.0,
                timestamp=datetime.fromisoformat(reg.get("Submitted_Date__c", reg["CreatedDate"])),
                source=DataSource.DEAL_REGISTRATION,
                source_id=reg["Id"],
                source_confidence=1.0,  # Deal reg = definitive
                deal_reg_status=reg.get("Status__c", "pending"),
                deal_reg_submitted_date=datetime.fromisoformat(reg.get("Submitted_Date__c")) if reg.get("Submitted_Date__c") else None,
                requires_approval=True,
                approved_by=reg.get("Approved_By__c"),
                approval_timestamp=datetime.fromisoformat(reg.get("Approved_Date__c")) if reg.get("Approved_Date__c") else None,
                metadata={
                    "deal_reg_name": reg.get("Name"),
                    "opportunity_id": reg.get("Opportunity__c"),
                    "estimated_value": reg.get("Estimated_Value__c")
                }
            )
            touchpoints.append(touchpoint)

        return touchpoints

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _activity_to_touchpoint(self, activity: Dict, activity_type: str) -> Optional[PartnerTouchpoint]:
        """Convert Salesforce activity to touchpoint."""
        if not activity.get("WhoId"):
            return None

        timestamp = activity.get("ActivityDate") or activity.get("StartDateTime") or activity["CreatedDate"]

        return PartnerTouchpoint(
            id=0,
            partner_id=activity["WhoId"],  # TODO: Map Contact → Partner
            target_id=0,
            touchpoint_type=TouchpointType.ACTIVITY,
            role="Influence",
            weight=1.0,
            timestamp=datetime.fromisoformat(timestamp),
            source=DataSource.TOUCHPOINT_TRACKING,
            source_id=activity["Id"],
            source_confidence=0.6,  # Activity = indirect evidence
            metadata={
                "activity_type": activity_type,
                "subject": activity.get("Subject"),
                "what_id": activity.get("WhatId")
            }
        )

    def _format_id_list(self, ids: List[str]) -> str:
        """Format list of IDs for SOQL IN clause."""
        formatted = "','".join(ids)
        return f"('{formatted}')"

    # ========================================================================
    # Object Detection
    # ========================================================================

    def detect_partner_fields(self) -> List[Dict[str, str]]:
        """
        Auto-detect partner-related fields on Opportunity.

        Returns:
            List of field metadata: [{"name": "Partner__c", "label": "Partner", "type": "lookup"}]
        """
        metadata = self.sf.Opportunity.describe()
        partner_fields = []

        for field in metadata["fields"]:
            field_name = field["name"].lower()
            field_label = field["label"].lower()

            # Look for partner-related fields
            if any(keyword in field_name or keyword in field_label
                   for keyword in ["partner", "reseller", "influence", "channel"]):
                partner_fields.append({
                    "name": field["name"],
                    "label": field["label"],
                    "type": field["type"],
                    "referenceTo": field.get("referenceTo", [])
                })

        return partner_fields

    def detect_deal_reg_object(self) -> Optional[str]:
        """Auto-detect deal registration custom object."""
        # Get all custom objects
        objects = self.sf.describe()["sobjects"]

        for obj in objects:
            obj_name = obj["name"].lower()
            obj_label = obj["label"].lower()

            if "deal" in obj_name and "reg" in obj_name:
                return obj["name"]
            if "deal registration" in obj_label:
                return obj["name"]

        return None


# ============================================================================
# Sync Orchestrator
# ============================================================================

class SalesforceSyncOrchestrator:
    """
    Orchestrates full Salesforce sync based on customer segment.
    """

    def __init__(self, client: SalesforceClient):
        self.client = client

    def sync_segment_1(
        self,
        partner_field: str,
        role_field: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Tuple[List[AttributionTarget], List[PartnerTouchpoint]]:
        """
        Sync for Segment 1: Partner field already populated.

        Returns clean, definitive partner data.
        """
        return self.client.sync_opportunities_with_partner_field(
            partner_field=partner_field,
            role_field=role_field,
            since=since
        )

    def sync_segment_2(
        self,
        partner_field: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Tuple[List[AttributionTarget], List[PartnerTouchpoint]]:
        """
        Sync for Segment 2: Partners tagged indirectly.

        Returns partner field (if available) + activities + campaigns + contact roles.
        """
        targets = []
        touchpoints = []

        # Get partner field data if available
        if partner_field:
            t, tp = self.client.sync_opportunities_with_partner_field(partner_field, since=since)
            targets.extend(t)
            touchpoints.extend(tp)

        # Get all opportunity IDs for activity lookup
        opp_ids = [t.external_id for t in targets] if targets else None

        # Get activities
        activity_touchpoints = self.client.sync_activities_for_opportunities(opp_ids, since)
        touchpoints.extend(activity_touchpoints)

        # Get campaign members
        campaign_touchpoints = self.client.sync_campaign_members()
        touchpoints.extend(campaign_touchpoints)

        # Get contact roles
        contact_role_touchpoints = self.client.sync_contact_roles(opp_ids)
        touchpoints.extend(contact_role_touchpoints)

        return targets, touchpoints

    def sync_segment_3(
        self,
        deal_reg_object: str,
        since: Optional[datetime] = None
    ) -> Tuple[List[AttributionTarget], List[PartnerTouchpoint]]:
        """
        Sync for Segment 3: Greenfield with deal registrations.

        Returns deal registrations + any existing data.
        """
        # Start with deal registrations
        deal_reg_touchpoints = self.client.sync_deal_registrations(deal_reg_object, since)

        # Also sync any opportunities (for context)
        targets, partner_touchpoints = self.client.sync_opportunities_with_partner_field(
            partner_field="Partner__c",
            since=since
        )

        all_touchpoints = deal_reg_touchpoints + partner_touchpoints

        return targets, all_touchpoints


# ============================================================================
# Integration Status Tracker
# ============================================================================

class SalesforceIntegration:
    """Stores integration credentials and sync status."""

    def __init__(
        self,
        organization_id: str,
        access_token: str,
        refresh_token: str,
        instance_url: str,
        segment_mode: str,  # "segment_1", "segment_2", "segment_3"
        config: Dict[str, Any]
    ):
        self.organization_id = organization_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.instance_url = instance_url
        self.segment_mode = segment_mode
        self.config = config  # partner_field, role_field, deal_reg_object, etc.
        self.last_sync = None
        self.sync_status = "pending"
        self.created_at = datetime.now()
