"""
Migration script to update app.py to use the new modular structure.

This script reads the old app.py.backup and creates a new app.py that imports
and uses the new modules (db, rules, attribution, ai, utils).
"""

import re

# Read the backup
with open('app.py.backup', 'r') as f:
    content = f.read()

# New imports to add at the top
new_imports = """import json
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

# Import our new modules
from config import DB_PATH, LOG_LEVEL, LOG_FILE
from db import Database
from rules import RuleEngine
from attribution import AttributionEngine
from ai import AIFeatures
from models import PARTNER_ROLES, SCHEMA_VERSION, DEFAULT_SETTINGS
from utils import (
    safe_json_loads,
    dataframe_to_csv_download,
    setup_logging,
    render_apply_summary_dict
)

# Setup logging
setup_logging(LOG_LEVEL, LOG_FILE)

# Initialize database and engines
db = Database(DB_PATH)
rule_engine = RuleEngine(db)
attribution_engine = AttributionEngine(db, rule_engine)
ai_features = AIFeatures(db)
"""

# Find where imports end (before st.set_page_config)
import_section_end = content.find('st.set_page_config')

# Find where functions start (after PARTNER_ROLES definition)
functions_start = content.find('# ----------------------------\n# DB helpers')

# Find where the app starts (after reset_demo function)
app_start = content.find('# ----------------------------\n# App\n#')

# Extract sections
pre_config = content[:import_section_end]
config_and_style = content[import_section_end:functions_start]
app_section = content[app_start:]

# Create new app.py content
new_content = f"""{new_imports}

{config_and_style}

# Initialize database
db.init_db()
db.seed_data_if_empty()

# Helper function wrappers for compatibility
def read_sql(sql: str, params: tuple = ()) -> pd.DataFrame:
    return db.read_sql(sql, params)

def run_sql(sql: str, params: tuple = ()):
    db.run_sql(sql, params)

def get_setting(key: str, default: str) -> str:
    return db.get_setting(key, default)

def set_setting(key: str, value: str):
    db.set_setting(key, value)

def get_setting_bool(key: str, default: bool) -> bool:
    return db.get_setting_bool(key, default)

def set_setting_bool(key: str, value: bool):
    db.set_setting_bool(key, value)

def should_enforce_split_cap() -> bool:
    return attribution_engine.should_enforce_split_cap()

def will_exceed_split_cap(account_id: str, partner_id: str, new_split: float):
    return attribution_engine.will_exceed_split_cap(account_id, partner_id, new_split)

def compute_si_auto_split(use_case_value: float, account_live_total: float, account_all_total: float, mode: str):
    return attribution_engine.compute_si_auto_split(use_case_value, account_live_total, account_all_total, mode)

def upsert_account_partner_from_use_case_partner(use_case_id: str, partner_id: str, partner_role: str, split_percent: float):
    result = attribution_engine.upsert_account_partner_from_use_case_partner(use_case_id, partner_id, partner_role, split_percent)
    return {{"status": result.status, "account_id": result.account_id, "total_with_new": result.total_with_new}}

def upsert_manual_account_partner(account_id: str, partner_id: str, split_percent: float):
    result = attribution_engine.upsert_manual_account_partner(account_id, partner_id, split_percent)
    return {{"status": result.status, "account_id": result.account_id, "total_with_new": result.total_with_new}}

def apply_rules_auto_assign(account_rollup_enabled: bool):
    summary = attribution_engine.apply_rules_auto_assign(account_rollup_enabled)
    return {{
        "applied": summary.applied,
        "blocked_rule": summary.blocked_rule,
        "blocked_cap": summary.blocked_cap,
        "skipped_manual": summary.skipped_manual,
        "details": summary.details
    }}

def recompute_attribution_ledger(days: int = 30):
    result = attribution_engine.recompute_attribution_ledger(days)
    return {{"inserted": result.inserted, "skipped": result.skipped, "blocked": result.blocked}}

def simulate_rule_impact(key: str, days: int = 60):
    result = attribution_engine.simulate_rule_impact(key, days)
    return {{
        "target": result.target,
        "lookback_days": result.lookback_days,
        "checked": result.checked,
        "allowed": result.allowed,
        "blocked": result.blocked,
        "no_context": result.no_context,
        "revenue_at_risk": result.revenue_at_risk,
        "estimated_value_blocked": result.estimated_value_blocked,
        "details": result.details
    }}

def recompute_explanations(account_id: str):
    return attribution_engine.recompute_explanations(account_id)

def create_use_case(account_id: str, use_case_name: str, stage: str, estimated_value: float, target_close_date: str, tag_source: str = "app"):
    return attribution_engine.create_use_case(account_id, use_case_name, stage, estimated_value, target_close_date, tag_source)

def reset_demo():
    db.reset_demo()

def load_rules(key: str):
    return rule_engine.load_rules(key)

def evaluate_rules(ctx: dict, key: str):
    result = rule_engine.evaluate_rules(ctx, key)
    return (result.allowed, result.message, result.matched_any_rule, result.matched_rule_index, result.rule_name)

def generate_rule_suggestion():
    return rule_engine.generate_rule_suggestion()

def validate_rule_obj(rule: dict) -> bool:
    return rule_engine.validate_rule_obj(rule)

def convert_nl_to_rule(text: str):
    return ai_features.convert_nl_to_rule(text)

def generate_relationship_summary(account_id: str):
    return ai_features.generate_relationship_summary(account_id)

def generate_ai_recommendations(account_id: str):
    return ai_features.generate_ai_recommendations(account_id)

def apply_recommendations(account_id: str, recs: list):
    return ai_features.apply_recommendations(account_id, recs, attribution_engine)

def infer_partner_role(account_name: str, use_case_name: str, partner_name: str, context: str):
    return ai_features.infer_partner_role(account_name, use_case_name, partner_name, context)

def render_apply_summary(summary: dict):
    msg = render_apply_summary_dict(summary)
    total_touched = sum(summary.get(k, 0) for k in ["applied", "blocked_rule", "blocked_cap", "skipped_manual"])
    if total_touched == 0:
        st.warning(msg)
    else:
        st.info(msg)
    details = summary.get("details", [])
    if details:
        st.caption("Notes: " + " | ".join(details[:5]))

{app_section}
"""

# Write the new app.py
with open('app.py', 'w') as f:
    f.write(new_content)

print("Migration complete! app.py has been updated to use the new modular structure.")
print("The old version is saved as app.py.backup")
