"""Utility functions and validation helpers."""

import json
import io
import logging
from typing import Any, Optional
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def safe_json_loads(payload: str) -> Optional[Any]:
    """Safely load JSON, returning None on error."""
    try:
        return json.loads(payload)
    except Exception as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return None


def validate_split_percent(split: float) -> bool:
    """Validate that a split percentage is in valid range [0, 1]."""
    return 0.0 <= split <= 1.0


def validate_partner_role(role: str, valid_roles: list) -> bool:
    """Validate that a partner role is in the list of valid roles."""
    return role in valid_roles


def format_currency(amount: float) -> str:
    """Format a currency amount."""
    return f"${amount:,.2f}"


def format_percent(pct: float) -> str:
    """Format a percentage."""
    return f"{pct * 100:.1f}%"


def dataframe_to_csv_download(df: pd.DataFrame, filename: str) -> tuple:
    """
    Convert a DataFrame to CSV for download.

    Returns (csv_bytes, filename).
    """
    if df.empty:
        logger.warning(f"Empty DataFrame for export: {filename}")
        return b"", filename

    # Create CSV in memory
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    csv_bytes = buffer.getvalue().encode('utf-8')

    logger.info(f"Exported {len(df)} rows to {filename}")
    return csv_bytes, filename


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.error(f"Failed to setup file logging: {e}")

    logger.info(f"Logging configured at level {log_level}")


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Trim to max length
    text = str(text)[:max_length]

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def validate_date_format(date_str: str) -> bool:
    """Validate that a string is a valid ISO date (YYYY-MM-DD)."""
    try:
        datetime.fromisoformat(date_str)
        return True
    except (ValueError, TypeError):
        return False


def render_apply_summary_dict(summary: dict) -> str:
    """
    Render an apply summary as a formatted string.

    Args:
        summary: Dict with keys applied, blocked_rule, blocked_cap, skipped_manual

    Returns:
        Formatted summary string
    """
    msg = (
        f"Auto-applied: {summary.get('applied', 0)} | "
        f"Blocked by rules: {summary.get('blocked_rule', 0)} | "
        f"Blocked by split cap: {summary.get('blocked_cap', 0)} | "
        f"Skipped (manual sources): {summary.get('skipped_manual', 0)}"
    )

    total_touched = sum(summary.get(k, 0) for k in ["applied", "blocked_rule", "blocked_cap", "skipped_manual"])

    if total_touched == 0:
        return msg + " — no links processed. Ensure you have Use Case ↔ Partner links and at least one allow rule."

    return msg
