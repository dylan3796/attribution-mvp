"""
Data Ingestion - CSV Upload and Schema Inference
=================================================

This module handles:
1. CSV upload and parsing
2. Schema detection (opportunity-based vs consumption-based)
3. Field mapping (user's columns → our universal schema)
4. Data validation and quality checks
5. Loading data into AttributionTarget + PartnerTouchpoint tables

The key challenge: Users have wildly different CSV schemas.
- Salesforce: OpportunityId, Amount, StageName, Partner__c, Partner_Role__c
- HubSpot: dealname, amount, dealstage, associatedcompanyids
- Custom: Whatever the user has

Our job: Infer their schema and map it to our universal tables.
"""

import pandas as pd
import io
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from models import (
    AttributionTarget,
    PartnerTouchpoint,
    TargetType,
    TouchpointType
)


# ============================================================================
# Schema Detection
# ============================================================================

class SchemaDetector:
    """
    Infer the schema of a CSV file.

    Detects:
    - Is this opportunity-based or consumption-based data?
    - Which columns map to target fields (id, value, timestamp)?
    - Which columns map to partner fields (partner_id, role, weight)?
    """

    # Common column name patterns
    TARGET_ID_PATTERNS = [
        "opportunity_id", "opportunityid", "opp_id", "id",
        "deal_id", "dealid", "event_id", "consumption_id", "target_id"
    ]

    VALUE_PATTERNS = [
        "amount", "value", "revenue", "deal_amount", "opp_amount",
        "consumption_amount", "usage_value", "mrr", "arr"
    ]

    TIMESTAMP_PATTERNS = [
        "close_date", "closedate", "closed_date", "deal_date",
        "event_date", "consumption_date", "timestamp", "date",
        "created_date", "updated_date"
    ]

    PARTNER_ID_PATTERNS = [
        "partner_id", "partner", "partner_name", "partnername",
        "partner__c", "partner_1__c", "partner_company", "reseller_id"
    ]

    PARTNER_ROLE_PATTERNS = [
        "partner_role", "role", "partner_type", "partnertype",
        "partner_role__c", "relationship_type", "involvement"
    ]

    PARTNER_WEIGHT_PATTERNS = [
        "weight", "activity_count", "meetings", "touches",
        "engagement_score", "influence_score"
    ]

    def infer_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze CSV columns and infer the schema.

        Returns:
            {
                "target_type": "opportunity" | "consumption" | "unknown",
                "mappings": {
                    "target_id": "opportunity_id",
                    "value": "amount",
                    "timestamp": "close_date",
                    "partner_id": "partner__c",
                    "partner_role": "partner_role__c",
                    ...
                },
                "confidence": 0.0-1.0,
                "warnings": [...]
            }
        """

        columns = [col.lower().strip() for col in df.columns]
        mappings = {}
        warnings = []

        # Detect target_id column
        target_id_col = self._find_best_match(columns, self.TARGET_ID_PATTERNS)
        if target_id_col:
            mappings["target_id"] = target_id_col
        else:
            warnings.append("Could not detect target ID column (opportunity_id, deal_id, etc.)")

        # Detect value column
        value_col = self._find_best_match(columns, self.VALUE_PATTERNS)
        if value_col:
            mappings["value"] = value_col
        else:
            warnings.append("Could not detect value column (amount, revenue, etc.)")

        # Detect timestamp column
        timestamp_col = self._find_best_match(columns, self.TIMESTAMP_PATTERNS)
        if timestamp_col:
            mappings["timestamp"] = timestamp_col
        else:
            warnings.append("Could not detect timestamp column (close_date, date, etc.)")

        # Detect partner columns
        partner_id_col = self._find_best_match(columns, self.PARTNER_ID_PATTERNS)
        if partner_id_col:
            mappings["partner_id"] = partner_id_col
        else:
            warnings.append("Could not detect partner ID column")

        partner_role_col = self._find_best_match(columns, self.PARTNER_ROLE_PATTERNS)
        if partner_role_col:
            mappings["partner_role"] = partner_role_col

        partner_weight_col = self._find_best_match(columns, self.PARTNER_WEIGHT_PATTERNS)
        if partner_weight_col:
            mappings["partner_weight"] = partner_weight_col

        # Infer target type (opportunity vs consumption)
        target_type = self._infer_target_type(columns)

        # Calculate confidence score
        confidence = len(mappings) / 4.0  # 4 critical fields (target_id, value, timestamp, partner_id)

        return {
            "target_type": target_type,
            "mappings": mappings,
            "confidence": min(confidence, 1.0),
            "warnings": warnings
        }

    def _find_best_match(self, columns: List[str], patterns: List[str]) -> Optional[str]:
        """
        Find the best matching column for a set of patterns.

        Uses exact match first, then substring match.
        """
        # Try exact match
        for pattern in patterns:
            if pattern in columns:
                return pattern

        # Try substring match
        for pattern in patterns:
            for col in columns:
                if pattern in col:
                    return col

        return None

    def _infer_target_type(self, columns: List[str]) -> str:
        """
        Guess whether this is opportunity-based or consumption-based data.
        """
        # Look for keywords that suggest opportunity data
        opp_keywords = ["opportunity", "deal", "opp", "stage", "close"]
        consumption_keywords = ["consumption", "usage", "event", "metered"]

        opp_score = sum(1 for col in columns if any(kw in col for kw in opp_keywords))
        consumption_score = sum(1 for col in columns if any(kw in col for kw in consumption_keywords))

        if opp_score > consumption_score:
            return "opportunity"
        elif consumption_score > opp_score:
            return "consumption"
        else:
            return "unknown"


# ============================================================================
# Data Validation
# ============================================================================

class DataValidator:
    """
    Validate data quality and detect common issues.
    """

    def validate_targets(self, df: pd.DataFrame, mappings: Dict[str, str]) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate target data (opportunities/consumption events).

        Returns: (valid_df, errors)
        """
        errors = []

        # Check required columns exist
        required = ["target_id", "value", "timestamp"]
        for field in required:
            if field not in mappings or mappings[field] not in df.columns:
                errors.append(f"Missing required field: {field}")

        if errors:
            return df, errors

        # Extract mapped columns
        target_id_col = mappings["target_id"]
        value_col = mappings["value"]
        timestamp_col = mappings["timestamp"]

        # Validate target_id (non-null, non-empty)
        null_ids = df[target_id_col].isnull().sum()
        if null_ids > 0:
            errors.append(f"{null_ids} rows have null target_id - will be skipped")
            df = df[df[target_id_col].notnull()]

        # Validate value (numeric, > 0)
        if not pd.api.types.is_numeric_dtype(df[value_col]):
            # Try to convert (remove $ and commas)
            df[value_col] = df[value_col].astype(str).str.replace('$', '').str.replace(',', '')
            try:
                df[value_col] = pd.to_numeric(df[value_col])
            except:
                errors.append(f"Value column '{value_col}' contains non-numeric data")

        negative_values = (df[value_col] < 0).sum()
        if negative_values > 0:
            errors.append(f"{negative_values} rows have negative values - will be set to 0")
            df.loc[df[value_col] < 0, value_col] = 0

        # Validate timestamp (valid dates)
        try:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        except:
            errors.append(f"Timestamp column '{timestamp_col}' contains invalid dates")

        return df, errors

    def validate_touchpoints(self, df: pd.DataFrame, mappings: Dict[str, str]) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate partner touchpoint data.

        Returns: (valid_df, errors)
        """
        errors = []

        # Check required columns
        if "partner_id" not in mappings:
            errors.append("Missing partner_id column - cannot create touchpoints")
            return df, errors

        partner_id_col = mappings["partner_id"]

        # Validate partner_id (non-null, non-empty)
        null_partners = df[partner_id_col].isnull().sum()
        if null_partners > 0:
            errors.append(f"{null_partners} rows have null partner_id - will be skipped")
            df = df[df[partner_id_col].notnull()]

        empty_partners = (df[partner_id_col].astype(str).str.strip() == "").sum()
        if empty_partners > 0:
            errors.append(f"{empty_partners} rows have empty partner_id - will be skipped")
            df = df[df[partner_id_col].astype(str).str.strip() != ""]

        # Validate partner_weight (if present)
        if "partner_weight" in mappings:
            weight_col = mappings["partner_weight"]
            if weight_col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[weight_col]):
                    try:
                        df[weight_col] = pd.to_numeric(df[weight_col])
                    except:
                        errors.append(f"Weight column '{weight_col}' contains non-numeric data - using default weight of 1.0")
                        df[weight_col] = 1.0

                negative_weights = (df[weight_col] < 0).sum()
                if negative_weights > 0:
                    errors.append(f"{negative_weights} rows have negative weights - will be set to 0")
                    df.loc[df[weight_col] < 0, weight_col] = 0

        return df, errors


# ============================================================================
# Data Loading
# ============================================================================

class DataLoader:
    """
    Load validated data into AttributionTarget and PartnerTouchpoint objects.
    """

    def load_targets_from_csv(
        self,
        df: pd.DataFrame,
        mappings: Dict[str, str],
        target_type: TargetType = TargetType.OPPORTUNITY
    ) -> List[AttributionTarget]:
        """
        Convert CSV rows to AttributionTarget objects.

        Args:
            df: Validated DataFrame
            mappings: Column name mappings
            target_type: Type of targets being loaded

        Returns:
            List of AttributionTarget objects (not yet saved to DB)
        """
        targets = []

        target_id_col = mappings["target_id"]
        value_col = mappings["value"]
        timestamp_col = mappings["timestamp"]

        # Get all other columns as metadata
        metadata_cols = [col for col in df.columns if col not in [target_id_col, value_col, timestamp_col]]

        for idx, row in df.iterrows():
            # Build metadata dict from remaining columns
            metadata = {}
            for col in metadata_cols:
                val = row[col]
                if pd.notna(val):
                    metadata[col] = str(val) if not isinstance(val, (int, float, bool)) else val

            target = AttributionTarget(
                id=0,  # Will be assigned by database
                type=target_type,
                external_id=str(row[target_id_col]),
                value=float(row[value_col]),
                timestamp=pd.to_datetime(row[timestamp_col]),
                metadata=metadata
            )

            targets.append(target)

        return targets

    def load_touchpoints_from_csv(
        self,
        df: pd.DataFrame,
        mappings: Dict[str, str],
        target_lookup: Dict[str, int],  # {external_id: target.id}
        touchpoint_type: TouchpointType = TouchpointType.TAGGED
    ) -> List[PartnerTouchpoint]:
        """
        Convert CSV rows to PartnerTouchpoint objects.

        Args:
            df: Validated DataFrame
            mappings: Column name mappings
            target_lookup: Map external_id to target.id (for FK)
            touchpoint_type: Type of touchpoint evidence

        Returns:
            List of PartnerTouchpoint objects (not yet saved to DB)
        """
        touchpoints = []

        target_id_col = mappings["target_id"]
        partner_id_col = mappings["partner_id"]
        role_col = mappings.get("partner_role")
        weight_col = mappings.get("partner_weight")
        timestamp_col = mappings.get("timestamp")  # Optional for touchpoints

        for idx, row in df.iterrows():
            external_id = str(row[target_id_col])

            # Look up the target.id
            if external_id not in target_lookup:
                # Target wasn't loaded (validation failed) - skip touchpoint
                continue

            target_id = target_lookup[external_id]

            # Extract partner fields
            partner_id = str(row[partner_id_col]).strip()
            role = str(row[role_col]) if role_col and role_col in df.columns else "Unknown"
            weight = float(row[weight_col]) if weight_col and weight_col in df.columns else 1.0

            # Touchpoint timestamp (may be same as target timestamp, or earlier)
            if timestamp_col and timestamp_col in df.columns:
                tp_timestamp = pd.to_datetime(row[timestamp_col])
            else:
                tp_timestamp = None

            # Build metadata
            metadata = {}
            for col in df.columns:
                if col not in [target_id_col, partner_id_col, role_col, weight_col, timestamp_col]:
                    val = row[col]
                    if pd.notna(val):
                        metadata[col] = str(val)

            touchpoint = PartnerTouchpoint(
                id=0,  # Will be assigned by database
                partner_id=partner_id,
                target_id=target_id,
                touchpoint_type=touchpoint_type,
                role=role,
                weight=weight,
                timestamp=tp_timestamp,
                metadata=metadata
            )

            touchpoints.append(touchpoint)

        return touchpoints


# ============================================================================
# Main Ingestion Pipeline
# ============================================================================

def ingest_csv(
    csv_content: bytes,
    user_mappings: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Complete CSV ingestion pipeline.

    Steps:
    1. Parse CSV
    2. Detect schema (or use user-provided mappings)
    3. Validate data
    4. Load into AttributionTarget + PartnerTouchpoint objects
    5. Return results (caller saves to database)

    Args:
        csv_content: Raw CSV bytes
        user_mappings: Optional manual column mappings (overrides auto-detection)

    Returns:
        {
            "targets": [AttributionTarget, ...],
            "touchpoints": [PartnerTouchpoint, ...],
            "schema": {...},
            "validation_errors": [...],
            "stats": {
                "targets_loaded": 10,
                "touchpoints_loaded": 15,
                "targets_skipped": 2,
                "warnings": [...]
            }
        }
    """

    # Step 1: Parse CSV
    df = pd.read_csv(io.BytesIO(csv_content))

    if df.empty:
        return {
            "targets": [],
            "touchpoints": [],
            "schema": {},
            "validation_errors": ["CSV file is empty"],
            "stats": {"targets_loaded": 0, "touchpoints_loaded": 0, "targets_skipped": 0}
        }

    # Step 2: Detect schema (or use user mappings)
    detector = SchemaDetector()
    if user_mappings:
        schema_info = {
            "target_type": user_mappings.get("target_type", "opportunity"),
            "mappings": user_mappings,
            "confidence": 1.0,
            "warnings": []
        }
    else:
        schema_info = detector.infer_schema(df)

    # Step 3: Validate data
    validator = DataValidator()

    targets_df, target_errors = validator.validate_targets(df, schema_info["mappings"])
    touchpoints_df, touchpoint_errors = validator.validate_touchpoints(df, schema_info["mappings"])

    all_errors = target_errors + touchpoint_errors + schema_info["warnings"]

    # Step 4: Load data into objects
    loader = DataLoader()

    target_type = TargetType.OPPORTUNITY if schema_info["target_type"] == "opportunity" else TargetType.CONSUMPTION_EVENT

    targets = loader.load_targets_from_csv(
        targets_df,
        schema_info["mappings"],
        target_type=target_type
    )

    # Build lookup map {external_id: target.id}
    # Note: target.id is 0 until saved to DB
    # For now, use external_id as temporary lookup (caller will update after DB insert)
    target_lookup = {t.external_id: idx for idx, t in enumerate(targets)}

    touchpoints = loader.load_touchpoints_from_csv(
        touchpoints_df,
        schema_info["mappings"],
        target_lookup=target_lookup,
        touchpoint_type=TouchpointType.TAGGED
    )

    # Step 5: Return results
    stats = {
        "targets_loaded": len(targets),
        "touchpoints_loaded": len(touchpoints),
        "targets_skipped": len(df) - len(targets),
        "warnings": all_errors
    }

    return {
        "targets": targets,
        "touchpoints": touchpoints,
        "schema": schema_info,
        "validation_errors": all_errors,
        "stats": stats
    }


# ============================================================================
# CSV Template Generation
# ============================================================================

def generate_csv_template(template_type: str = "salesforce") -> str:
    """
    Generate a CSV template for users to fill out.

    Args:
        template_type: "salesforce", "hubspot", or "minimal"

    Returns:
        CSV string (ready to download)
    """

    if template_type == "salesforce":
        return """opportunity_id,amount,close_date,stage_name,partner__c,partner_role__c
006ABC123,100000,2025-01-15,Closed Won,Acme Consulting,Implementation (SI)
006ABC124,50000,2025-01-20,Negotiation,Tech Partners Inc,Influence
006ABC125,75000,2025-01-25,Closed Won,Acme Consulting,Implementation (SI)
"""

    elif template_type == "hubspot":
        return """deal_id,amount,close_date,dealstage,partner_id,partner_role
12345,100000,2025-01-15,closedwon,acme-consulting,SI
12346,50000,2025-01-20,negotiation,tech-partners-inc,Influence
12347,75000,2025-01-25,closedwon,acme-consulting,SI
"""

    else:  # minimal
        return """target_id,value,timestamp,partner_id,role
T001,100000,2025-01-15,Partner A,Implementation (SI)
T002,50000,2025-01-20,Partner B,Influence
T003,75000,2025-01-25,Partner A,Implementation (SI)
"""


# ============================================================================
# Multi-Source Data Ingestion (Phase 3)
# ============================================================================

class DataSourceIngestion:
    """
    Ingest partner data from specific source types with proper source tracking.

    This class handles the conversion of source-specific data formats
    into PartnerTouchpoint objects with correct DataSource attribution.

    Supports:
    - Deal registrations (partner-submitted)
    - Marketplace transactions (AWS/Azure/GCP)
    - CRM partner fields (Salesforce Partner__c, etc.)
    - Partner self-reported activities
    - Integration tags (Slack, Jira, etc.)
    """

    def __init__(self):
        """Initialize data source ingestion handler."""
        # Import here to avoid circular dependency
        from models import DataSource, MeasurementWorkflow
        self.DataSource = DataSource
        self.MeasurementWorkflow = MeasurementWorkflow

    def ingest_deal_registrations(
        self,
        csv_content: bytes,
        workflow: Optional[Any] = None,
        target_id_mapping: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Ingest partner-submitted deal registrations from CSV.

        CSV Schema (required columns):
        - deal_reg_id: Unique deal registration ID
        - partner_id: Partner identifier
        - opportunity_id: External opportunity ID
        - submitted_date: When partner submitted the deal reg

        Optional columns:
        - partner_role: Partner's role (defaults to "Referral")
        - status: pending/approved/rejected/expired (defaults to "pending")
        - approved_by: User who approved
        - approval_date: When approved

        Args:
            csv_content: CSV file content as bytes
            workflow: Optional MeasurementWorkflow for validation rules
            target_id_mapping: Optional dict mapping external_id → target_id

        Returns:
            {
                "touchpoints": List[PartnerTouchpoint],
                "count": int,
                "warnings": List[str],
                "stats": {...}
            }
        """
        from models import DataSource

        try:
            # Parse CSV
            df = pd.read_csv(io.BytesIO(csv_content))

            # Validate required columns
            required_cols = ["deal_reg_id", "partner_id", "opportunity_id", "submitted_date"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            touchpoints = []
            warnings = []
            stats = {
                "total_rows": len(df),
                "touchpoints_created": 0,
                "skipped_rows": 0,
                "by_status": {}
            }

            # Get validation config from workflow
            require_approval = False
            if workflow and hasattr(workflow, 'data_sources'):
                deal_reg_config = next(
                    (ds for ds in workflow.data_sources
                     if ds.source_type == DataSource.DEAL_REGISTRATION),
                    None
                )
                if deal_reg_config:
                    require_approval = deal_reg_config.config.get("require_approval", False)

            for idx, row in df.iterrows():
                try:
                    # Parse submitted date
                    submitted_date = pd.to_datetime(row["submitted_date"])

                    # Determine target_id
                    target_id = 0  # Placeholder (will be resolved by caller)
                    if target_id_mapping and row["opportunity_id"] in target_id_mapping:
                        target_id = target_id_mapping[row["opportunity_id"]]

                    # Get status (default to pending)
                    status = row.get("status", "pending")
                    stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                    # Create touchpoint
                    touchpoint = PartnerTouchpoint(
                        id=0,  # Will be assigned by database
                        partner_id=str(row["partner_id"]),
                        target_id=target_id,
                        touchpoint_type=TouchpointType.DEAL_REGISTRATION,
                        role=row.get("partner_role", "Referral"),
                        weight=1.0,
                        timestamp=submitted_date,

                        # Source tracking (Phase 1.3)
                        source=DataSource.DEAL_REGISTRATION,
                        source_id=str(row["deal_reg_id"]),
                        source_confidence=1.0,  # Deal reg is definitive

                        # Deal registration fields
                        deal_reg_status=status,
                        deal_reg_submitted_date=submitted_date,
                        deal_reg_approved_date=pd.to_datetime(row["approval_date"]) if "approval_date" in row and pd.notna(row["approval_date"]) else None,

                        # Approval workflow
                        requires_approval=require_approval,
                        approved_by=row.get("approved_by") if "approved_by" in row else None,
                        approval_timestamp=pd.to_datetime(row["approval_date"]) if "approval_date" in row and pd.notna(row["approval_date"]) else None,

                        # Metadata
                        metadata={
                            "opportunity_id": row["opportunity_id"],
                            "estimated_value": float(row["estimated_value"]) if "estimated_value" in row and pd.notna(row["estimated_value"]) else None,
                            "notes": row.get("notes")
                        },
                        created_at=datetime.now()
                    )

                    touchpoints.append(touchpoint)
                    stats["touchpoints_created"] += 1

                except Exception as e:
                    warnings.append(f"Row {idx + 1}: {str(e)}")
                    stats["skipped_rows"] += 1

            return {
                "touchpoints": touchpoints,
                "count": len(touchpoints),
                "warnings": warnings,
                "stats": stats
            }

        except Exception as e:
            raise ValueError(f"Error ingesting deal registrations: {e}")

    def ingest_crm_partner_field(
        self,
        opportunities: List[Dict[str, Any]],
        field_config: Dict[str, str],
        target_id_mapping: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Ingest from single CRM partner field (e.g., Salesforce Partner__c).

        Opportunity schema (dict keys):
        - id: Opportunity external ID
        - created_date: When opportunity was created
        - [field_config["field_name"]]: Partner value

        Field config:
        - field_name: Name of partner field (e.g., "Partner__c")
        - role_field: Optional name of role field (e.g., "Partner_Role__c")

        Args:
            opportunities: List of opportunity dicts
            field_config: {"field_name": "Partner__c", "role_field": "Partner_Role__c"}
            target_id_mapping: Optional dict mapping external_id → target_id

        Returns:
            {
                "touchpoints": List[PartnerTouchpoint],
                "count": int,
                "warnings": List[str],
                "stats": {...}
            }
        """
        from models import DataSource

        touchpoints = []
        warnings = []
        stats = {
            "total_opps": len(opportunities),
            "with_partner": 0,
            "without_partner": 0
        }

        partner_field = field_config.get("field_name", "Partner__c")
        role_field = field_config.get("role_field")

        for idx, opp in enumerate(opportunities):
            try:
                # Check if partner field is populated
                if partner_field not in opp or not opp[partner_field]:
                    stats["without_partner"] += 1
                    continue  # No partner tagged

                stats["with_partner"] += 1

                # Parse created date
                created_date = pd.to_datetime(opp.get("created_date", datetime.now()))

                # Determine target_id
                target_id = 0  # Placeholder
                if target_id_mapping and "id" in opp:
                    target_id = target_id_mapping.get(opp["id"], 0)

                # Get partner role
                role = "Unknown"
                if role_field and role_field in opp and opp[role_field]:
                    role = opp[role_field]

                # Create touchpoint
                touchpoint = PartnerTouchpoint(
                    id=0,
                    partner_id=str(opp[partner_field]),
                    target_id=target_id,
                    touchpoint_type=TouchpointType.CRM_PARTNER_FIELD,
                    role=role,
                    weight=1.0,
                    timestamp=created_date,

                    # Source tracking
                    source=DataSource.CRM_OPPORTUNITY_FIELD,
                    source_id=opp.get("id"),
                    source_confidence=1.0,  # CRM field is definitive

                    # Metadata
                    metadata={
                        "crm_field": partner_field,
                        "opportunity_id": opp.get("id"),
                        "opportunity_name": opp.get("name"),
                        "stage": opp.get("stage"),
                        "amount": opp.get("amount")
                    },
                    created_at=datetime.now()
                )

                touchpoints.append(touchpoint)

            except Exception as e:
                warnings.append(f"Opportunity {idx}: {str(e)}")

        return {
            "touchpoints": touchpoints,
            "count": len(touchpoints),
            "warnings": warnings,
            "stats": stats
        }

    def create_target_id_mapping(self, targets: List[Any]) -> Dict[str, int]:
        """
        Create a mapping from external_id to target_id for fast lookups.

        Args:
            targets: List of AttributionTarget objects

        Returns:
            Dict mapping external_id → target_id
        """
        return {target.external_id: target.id for target in targets}
