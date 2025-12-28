"""
Bulk import/export operations for Attribution MVP.
Supports batch operations for accounts, partners, use cases, and relationships.
"""

import pandas as pd
import io
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def import_accounts_from_csv(csv_content: bytes, db) -> Tuple[int, int, List[str]]:
    """
    Import accounts from CSV file.

    Expected columns: account_id, account_name

    Args:
        csv_content: CSV file content as bytes
        db: Database instance

    Returns:
        Tuple of (success_count, error_count, error_messages)
    """
    success_count = 0
    error_count = 0
    errors = []

    try:
        df = pd.read_csv(io.BytesIO(csv_content))

        # Validate required columns
        required_cols = ['account_id', 'account_name']
        missing = set(required_cols) - set(df.columns)
        if missing:
            return 0, len(df), [f"Missing required columns: {missing}"]

        for idx, row in df.iterrows():
            try:
                db.run_sql("""
                    INSERT INTO accounts (account_id, account_name)
                    VALUES (?, ?)
                    ON CONFLICT(account_id) DO UPDATE SET
                        account_name = excluded.account_name;
                """, (row['account_id'], row['account_name']))
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Row {idx + 1}: {str(e)}")
                logger.error(f"Error importing account row {idx}: {e}")

    except Exception as e:
        return 0, 0, [f"Failed to parse CSV: {str(e)}"]

    return success_count, error_count, errors


def import_partners_from_csv(csv_content: bytes, db) -> Tuple[int, int, List[str]]:
    """
    Import partners from CSV file.

    Expected columns: partner_id, partner_name

    Args:
        csv_content: CSV file content as bytes
        db: Database instance

    Returns:
        Tuple of (success_count, error_count, error_messages)
    """
    success_count = 0
    error_count = 0
    errors = []

    try:
        df = pd.read_csv(io.BytesIO(csv_content))

        # Validate required columns
        required_cols = ['partner_id', 'partner_name']
        missing = set(required_cols) - set(df.columns)
        if missing:
            return 0, len(df), [f"Missing required columns: {missing}"]

        for idx, row in df.iterrows():
            try:
                db.run_sql("""
                    INSERT INTO partners (partner_id, partner_name)
                    VALUES (?, ?)
                    ON CONFLICT(partner_id) DO UPDATE SET
                        partner_name = excluded.partner_name;
                """, (row['partner_id'], row['partner_name']))
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Row {idx + 1}: {str(e)}")
                logger.error(f"Error importing partner row {idx}: {e}")

    except Exception as e:
        return 0, 0, [f"Failed to parse CSV: {str(e)}"]

    return success_count, error_count, errors


def import_use_cases_from_csv(csv_content: bytes, db) -> Tuple[int, int, List[str]]:
    """
    Import use cases from CSV file.

    Expected columns: use_case_id, account_id, use_case_name, stage, estimated_value, target_close_date

    Args:
        csv_content: CSV file content as bytes
        db: Database instance

    Returns:
        Tuple of (success_count, error_count, error_messages)
    """
    success_count = 0
    error_count = 0
    errors = []

    try:
        df = pd.read_csv(io.BytesIO(csv_content))

        # Validate required columns
        required_cols = ['use_case_id', 'account_id', 'use_case_name', 'stage', 'estimated_value']
        missing = set(required_cols) - set(df.columns)
        if missing:
            return 0, len(df), [f"Missing required columns: {missing}"]

        for idx, row in df.iterrows():
            try:
                target_close_date = row.get('target_close_date', None)
                if pd.isna(target_close_date):
                    target_close_date = None

                db.run_sql("""
                    INSERT INTO use_cases (
                        use_case_id, account_id, use_case_name, stage,
                        estimated_value, target_close_date, tag_source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'import')
                    ON CONFLICT(use_case_id) DO UPDATE SET
                        use_case_name = excluded.use_case_name,
                        stage = excluded.stage,
                        estimated_value = excluded.estimated_value,
                        target_close_date = excluded.target_close_date;
                """, (
                    row['use_case_id'],
                    row['account_id'],
                    row['use_case_name'],
                    row['stage'],
                    float(row['estimated_value']) if pd.notna(row['estimated_value']) else None,
                    target_close_date
                ))
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Row {idx + 1}: {str(e)}")
                logger.error(f"Error importing use case row {idx}: {e}")

    except Exception as e:
        return 0, 0, [f"Failed to parse CSV: {str(e)}"]

    return success_count, error_count, errors


def import_use_case_partners_from_csv(csv_content: bytes, db) -> Tuple[int, int, List[str]]:
    """
    Import use case partner relationships from CSV file.

    Expected columns: use_case_id, partner_id, partner_role

    Args:
        csv_content: CSV file content as bytes
        db: Database instance

    Returns:
        Tuple of (success_count, error_count, error_messages)
    """
    success_count = 0
    error_count = 0
    errors = []

    try:
        df = pd.read_csv(io.BytesIO(csv_content))

        # Validate required columns
        required_cols = ['use_case_id', 'partner_id', 'partner_role']
        missing = set(required_cols) - set(df.columns)
        if missing:
            return 0, len(df), [f"Missing required columns: {missing}"]

        for idx, row in df.iterrows():
            try:
                created_at = datetime.now().date().isoformat()

                db.run_sql("""
                    INSERT INTO use_case_partners (
                        use_case_id, partner_id, partner_role, created_at
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(use_case_id, partner_id) DO UPDATE SET
                        partner_role = excluded.partner_role;
                """, (
                    row['use_case_id'],
                    row['partner_id'],
                    row['partner_role'],
                    created_at
                ))
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Row {idx + 1}: {str(e)}")
                logger.error(f"Error importing use case partner row {idx}: {e}")

    except Exception as e:
        return 0, 0, [f"Failed to parse CSV: {str(e)}"]

    return success_count, error_count, errors


def export_all_data(db) -> Dict[str, pd.DataFrame]:
    """
    Export all data tables for bulk backup.

    Args:
        db: Database instance

    Returns:
        Dictionary of {table_name: DataFrame}
    """
    tables = {}

    try:
        tables['accounts'] = db.read_sql("SELECT * FROM accounts;")
        tables['partners'] = db.read_sql("SELECT * FROM partners;")
        tables['use_cases'] = db.read_sql("SELECT * FROM use_cases;")
        tables['use_case_partners'] = db.read_sql("SELECT * FROM use_case_partners;")
        tables['account_partners'] = db.read_sql("SELECT * FROM account_partners;")
        tables['revenue_events'] = db.read_sql("SELECT * FROM revenue_events;")
        tables['attribution_events'] = db.read_sql("SELECT * FROM attribution_events;")
        tables['activities'] = db.read_sql("SELECT * FROM activities;")
        tables['audit_trail'] = db.read_sql("SELECT * FROM audit_trail;")

    except Exception as e:
        logger.error(f"Error exporting data: {e}")

    return tables


def get_import_template(entity_type: str) -> str:
    """
    Get CSV template for bulk import.

    Args:
        entity_type: Type of entity (accounts, partners, use_cases, use_case_partners)

    Returns:
        CSV template as string
    """
    templates = {
        'accounts': 'account_id,account_name\nACCT001,Example Account\nACCT002,Another Account',
        'partners': 'partner_id,partner_name\nPART001,Example Partner\nPART002,Another Partner',
        'use_cases': 'use_case_id,account_id,use_case_name,stage,estimated_value,target_close_date\nUC001,ACCT001,Example Use Case,Discovery,100000,2025-12-31\nUC002,ACCT001,Another Use Case,Evaluation,50000,2025-11-30',
        'use_case_partners': 'use_case_id,partner_id,partner_role\nUC001,PART001,Implementation (SI)\nUC001,PART002,Influence'
    }

    return templates.get(entity_type, '')


def bulk_update_splits(updates: List[Dict], db, attribution_engine) -> Tuple[int, int, List[str]]:
    """
    Bulk update partner splits.

    Args:
        updates: List of dictionaries with account_id, partner_id, split_percent
        db: Database instance
        attribution_engine: Attribution engine instance

    Returns:
        Tuple of (success_count, error_count, error_messages)
    """
    success_count = 0
    error_count = 0
    errors = []

    for idx, update in enumerate(updates):
        try:
            account_id = update.get('account_id')
            partner_id = update.get('partner_id')
            split_percent = float(update.get('split_percent', 0)) / 100.0

            result = attribution_engine.upsert_manual_account_partner(
                account_id=account_id,
                partner_id=partner_id,
                split_percent=split_percent
            )

            if result.status == "blocked_split_cap":
                error_count += 1
                errors.append(f"Update {idx + 1}: Split cap exceeded for {account_id}/{partner_id}")
            else:
                success_count += 1

        except Exception as e:
            error_count += 1
            errors.append(f"Update {idx + 1}: {str(e)}")
            logger.error(f"Error bulk updating split {idx}: {e}")

    return success_count, error_count, errors
