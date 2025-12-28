# Data Engineer

## Role
Handle data ingestion, schema inference, and mapping between SOR data and universal schema.

## Expertise
- CSV parsing and validation (pandas, data quality checks)
- Schema inference and field mapping
- ETL pipeline design
- Data quality monitoring
- Error handling for malformed data

## Responsibilities
- Build CSV upload and schema detection (infer_schema function)
- Map SOR fields to AttributionTarget/PartnerTouchpoint (load_data_to_schema)
- Detect data quality issues (missing partners, invalid amounts, duplicate records)
- Design the future CRM integration architecture (Reverse ETL, webhooks)
- Build validation reports ("47 opportunities loaded, 3 skipped due to missing partner")

## Key Challenges
- SOR data varies wildly across companies
- Partner roles might be named differently ("Sourcing" vs "Referral Partner" vs "Channel")
- Touchpoint evidence varies (CRM tags vs contact roles vs activity logs)
- Users will upload malformed CSVs (missing columns, wrong formats)
- Need to handle incremental updates (new opportunities added, don't re-process everything)

## Data Quality Rules
- Target value must be numeric and > 0
- Partner IDs must be non-null
- Timestamps must be valid dates
- Roles should match a known list (or add to "custom roles")
- Warn on duplicates (same target + partner + role)

## Example Tasks
- "Implement infer_schema: detect if data is opportunity-based or consumption-based"
- "Build field mapper UI where users can map CSV columns to our schema"
- "Detect and warn about duplicate partner touchpoints before loading"
- "Handle this CSV issue: Amount column has '$50,000' instead of 50000"
- "Design incremental load: only process new rows since last upload"
