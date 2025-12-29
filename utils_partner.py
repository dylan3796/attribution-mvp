"""
Partner Utilities Module
=========================

Helper functions for partner analytics and formatting.

Provides:
- Growth percentage calculations
- Trend indicators
- Time formatting
- Grade classifications
"""

from datetime import datetime, timedelta
from typing import Optional


# ============================================================================
# Growth & Trend Calculations
# ============================================================================

def calculate_growth_percentage(current: float, previous: float) -> float:
    """
    Calculate growth percentage.

    Args:
        current: Current period value
        previous: Previous period value

    Returns:
        Growth percentage (e.g., 0.15 for 15% growth)
    """
    if previous == 0:
        return 1.0 if current > 0 else 0.0

    return (current - previous) / previous


def get_trend_indicator(growth: float) -> str:
    """
    Get emoji trend indicator based on growth rate.

    Args:
        growth: Growth rate (e.g., 0.15 for 15% growth)

    Returns:
        Emoji: "🚀" (high growth), "↗" (growth), "→" (flat), "↘" (decline)
    """
    if growth >= 0.30:  # 30%+ growth
        return "🚀"
    elif growth >= 0.10:  # 10-30% growth
        return "↗"
    elif growth >= -0.10:  # -10% to 10% (flat)
        return "→"
    else:  # >10% decline
        return "↘"


def format_growth_percentage(growth: float, include_sign: bool = True) -> str:
    """
    Format growth percentage for display.

    Args:
        growth: Growth rate (e.g., 0.15 for 15% growth)
        include_sign: Include + sign for positive growth

    Returns:
        Formatted string (e.g., "+15.0%", "-5.2%")
    """
    pct = growth * 100

    if include_sign and pct > 0:
        return f"+{pct:.1f}%"
    else:
        return f"{pct:.1f}%"


# ============================================================================
# Time Formatting
# ============================================================================

def format_days_ago(timestamp: datetime) -> str:
    """
    Format timestamp as human-readable "X days/weeks/months ago".

    Args:
        timestamp: Datetime to format

    Returns:
        Formatted string (e.g., "3d ago", "2w ago", "1mo ago")
    """
    if not timestamp:
        return "N/A"

    now = datetime.now()
    delta = now - timestamp

    days = delta.days

    if days == 0:
        # Same day - show hours
        hours = delta.seconds // 3600
        if hours == 0:
            return "Just now"
        elif hours == 1:
            return "1h ago"
        else:
            return f"{hours}h ago"
    elif days == 1:
        return "Yesterday"
    elif days < 7:
        return f"{days}d ago"
    elif days < 30:
        weeks = days // 7
        return f"{weeks}w ago"
    elif days < 365:
        months = days // 30
        return f"{months}mo ago"
    else:
        years = days // 365
        return f"{years}y ago"


def format_days_count(days: int) -> str:
    """
    Format day count for display.

    Args:
        days: Number of days

    Returns:
        Formatted string (e.g., "45 days", "2 weeks", "3 months")
    """
    if days < 7:
        return f"{days} days"
    elif days < 30:
        weeks = days // 7
        remainder = days % 7
        if remainder == 0:
            return f"{weeks} {'week' if weeks == 1 else 'weeks'}"
        else:
            return f"{weeks}w {remainder}d"
    elif days < 365:
        months = days // 30
        return f"{months} {'month' if months == 1 else 'months'}"
    else:
        years = days // 365
        return f"{years} {'year' if years == 1 else 'years'}"


# ============================================================================
# Health Score & Grade Classification
# ============================================================================

def classify_health_grade(score: float) -> str:
    """
    Classify health score into letter grade.

    Args:
        score: Health score (0-100)

    Returns:
        Letter grade: "A", "B", "C", "D", "F"
    """
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def get_health_color(score: float) -> str:
    """
    Get color code for health score visualization.

    Args:
        score: Health score (0-100)

    Returns:
        Color hex code or color name
    """
    if score >= 70:
        return "#10b981"  # Green
    elif score >= 40:
        return "#f59e0b"  # Orange/Yellow
    else:
        return "#ef4444"  # Red


def get_health_emoji(score: float) -> str:
    """
    Get emoji for health score.

    Args:
        score: Health score (0-100)

    Returns:
        Emoji: 🟢 (good), 🟡 (warning), 🔴 (critical)
    """
    if score >= 70:
        return "🟢"
    elif score >= 40:
        return "🟡"
    else:
        return "🔴"


def get_grade_description(grade: str) -> str:
    """
    Get descriptive text for letter grade.

    Args:
        grade: Letter grade (A-F)

    Returns:
        Description text
    """
    descriptions = {
        "A": "Excellent Partner",
        "B": "Strong Performer",
        "C": "Solid Partner",
        "D": "Needs Attention",
        "F": "At Risk"
    }

    return descriptions.get(grade, "Unknown")


# ============================================================================
# Currency Formatting
# ============================================================================

def format_currency(amount: float, include_cents: bool = False) -> str:
    """
    Format amount as currency.

    Args:
        amount: Dollar amount
        include_cents: Include cents in formatting

    Returns:
        Formatted string (e.g., "$1,234,567", "$1,234.56")
    """
    if include_cents:
        return f"${amount:,.2f}"
    else:
        return f"${amount:,.0f}"


def format_currency_compact(amount: float) -> str:
    """
    Format amount as compact currency (K, M notation).

    Args:
        amount: Dollar amount

    Returns:
        Formatted string (e.g., "$1.2M", "$45K", "$123")
    """
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.0f}K"
    else:
        return f"${amount:.0f}"


# ============================================================================
# Percentage Formatting
# ============================================================================

def format_percentage(value: Optional[float], decimal_places: int = 1) -> str:
    """
    Format value as percentage.

    Args:
        value: Percentage value (0.0 to 1.0)
        decimal_places: Number of decimal places

    Returns:
        Formatted string (e.g., "65.5%", "N/A")
    """
    if value is None:
        return "N/A"

    pct = value * 100
    return f"{pct:.{decimal_places}f}%"


# ============================================================================
# Metric Formatting
# ============================================================================

def format_metric_delta(current: float, previous: float, format_type: str = "percentage") -> str:
    """
    Format delta between current and previous values.

    Args:
        current: Current value
        previous: Previous value
        format_type: "percentage", "currency", "number"

    Returns:
        Formatted delta string (e.g., "+15.0%", "+$50K")
    """
    if previous == 0:
        if current > 0:
            return "+100%"
        else:
            return "→ 0%"

    growth = (current - previous) / previous

    if format_type == "percentage":
        return format_growth_percentage(growth)
    elif format_type == "currency":
        delta = current - previous
        sign = "+" if delta > 0 else ""
        return f"{sign}{format_currency_compact(abs(delta))}"
    elif format_type == "number":
        delta = int(current - previous)
        sign = "+" if delta > 0 else ""
        return f"{sign}{delta}"
    else:
        return str(growth)


def format_optional_metric(value: Optional[float], formatter: callable, na_text: str = "N/A") -> str:
    """
    Format optional metric with N/A fallback.

    Args:
        value: Optional value
        formatter: Function to format non-None values
        na_text: Text to display when value is None

    Returns:
        Formatted string or na_text
    """
    if value is None:
        return na_text

    return formatter(value)
