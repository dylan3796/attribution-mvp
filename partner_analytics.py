"""
Partner Analytics Module
========================

Core analytics functions for partner management dashboards.

Provides:
- Health score calculation (0-100)
- Period comparison logic
- Alert detection
- Win rate and deal velocity metrics
- Partner insights generation
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import statistics

from models_new import AttributionTarget, PartnerTouchpoint, LedgerEntry


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class HealthScore:
    """Partner health score with component breakdown."""
    total_score: float  # 0-100
    grade: str  # A, B, C, D, F
    revenue_trend_score: float  # 0-35
    engagement_score: float  # 0-25
    win_rate_score: Optional[float]  # 0-20 or None
    deal_size_score: float  # 0-10
    consistency_score: float  # 0-10
    trend: str  # "↗️", "→", "↘️"


@dataclass
class PeriodComparison:
    """Comparison between current and previous periods."""
    current_revenue: float
    previous_revenue: float
    growth_percentage: float
    current_deals: int
    previous_deals: int
    deal_growth_percentage: float
    current_coverage: float  # Attribution coverage %
    previous_coverage: float


@dataclass
class Alert:
    """Alert notification."""
    severity: str  # "critical", "warning", "info"
    title: str
    description: str
    partner_id: Optional[str]
    partner_name: Optional[str]
    recommended_action: str
    timestamp: datetime


@dataclass
class PartnerChange:
    """Partner revenue change data."""
    partner_id: str
    partner_name: str
    current_revenue: float
    previous_revenue: float
    change_amount: float
    change_percentage: float
    trend_indicator: str  # "🚀", "↗", "→", "↘"


@dataclass
class PartnerInsights:
    """Partner strengths and improvement areas."""
    strengths: List[str]
    improvements: List[str]
    recommendations: List[str]


# ============================================================================
# Health Score Calculation
# ============================================================================

def calculate_health_score(
    partner_id: str,
    ledger: List[LedgerEntry],
    touchpoints: List[PartnerTouchpoint],
    targets: List[AttributionTarget],
    lookback_days: int = 90
) -> HealthScore:
    """
    Calculate partner health score (0-100).

    Components:
    - Revenue Trend (35 points): Growth vs decline
    - Engagement Level (25 points): Activity frequency
    - Win Rate (20 points): % of touched deals won (if stage data available)
    - Deal Size Trend (10 points): Average deal size trend
    - Consistency (10 points): Regular vs sporadic engagement
    """
    cutoff_date = datetime.now() - timedelta(days=lookback_days)

    # Filter to partner's data in lookback window
    partner_ledger = [e for e in ledger
                     if e.partner_id == partner_id
                     and e.calculation_timestamp >= cutoff_date]
    partner_touchpoints = [tp for tp in touchpoints
                          if tp.partner_id == partner_id
                          and tp.timestamp and tp.timestamp >= cutoff_date]

    # Component 1: Revenue Trend (35 points)
    revenue_score = _calculate_revenue_trend_score(partner_id, ledger)

    # Component 2: Engagement Level (25 points)
    engagement_score = _calculate_engagement_score(partner_touchpoints, lookback_days)

    # Component 3: Win Rate (20 points) - OPTIONAL
    win_rate_score = _calculate_win_rate_score(partner_id, targets, touchpoints)

    # Component 4: Deal Size Trend (10 points)
    deal_size_score = _calculate_deal_size_score(partner_ledger)

    # Component 5: Consistency (10 points)
    consistency_score = _calculate_consistency_score(partner_touchpoints)

    # Calculate total (handle optional win rate)
    if win_rate_score is not None:
        total = revenue_score + engagement_score + win_rate_score + deal_size_score + consistency_score
    else:
        # If no win rate data, redistribute those 20 points proportionally
        total = revenue_score + engagement_score + 15 + deal_size_score + consistency_score

    # Classify grade
    grade = _classify_health_grade(total)

    # Calculate trend (compare to previous period)
    prev_score = _calculate_previous_health_score(partner_id, ledger, touchpoints, targets, lookback_days)
    if prev_score is not None:
        if total > prev_score + 5:
            trend = "↗️"
        elif total < prev_score - 5:
            trend = "↘️"
        else:
            trend = "→"
    else:
        trend = "→"

    return HealthScore(
        total_score=round(total, 1),
        grade=grade,
        revenue_trend_score=round(revenue_score, 1),
        engagement_score=round(engagement_score, 1),
        win_rate_score=round(win_rate_score, 1) if win_rate_score is not None else None,
        deal_size_score=round(deal_size_score, 1),
        consistency_score=round(consistency_score, 1),
        trend=trend
    )


def _calculate_revenue_trend_score(partner_id: str, ledger: List[LedgerEntry]) -> float:
    """Revenue trend score (0-35): Compare last 30 days vs previous 30 days."""
    now = datetime.now()
    last_30_start = now - timedelta(days=30)
    prev_30_start = now - timedelta(days=60)
    prev_30_end = now - timedelta(days=30)

    # Revenue in last 30 days
    recent_revenue = sum(
        e.attributed_value for e in ledger
        if e.partner_id == partner_id
        and e.calculation_timestamp >= last_30_start
    )

    # Revenue in previous 30 days
    previous_revenue = sum(
        e.attributed_value for e in ledger
        if e.partner_id == partner_id
        and prev_30_start <= e.calculation_timestamp < prev_30_end
    )

    # Calculate growth
    if previous_revenue > 0:
        growth = (recent_revenue - previous_revenue) / previous_revenue
    elif recent_revenue > 0:
        growth = 1.0  # 100% growth from zero
    else:
        growth = 0.0

    # Score based on growth
    if growth >= 0.20:  # 20%+ growth
        return 35.0
    elif growth >= 0.10:  # 10-20% growth
        return 30.0
    elif growth >= 0:  # Flat to 10% growth
        return 25.0
    elif growth >= -0.10:  # Small decline
        return 15.0
    else:  # Large decline
        return 5.0


def _calculate_engagement_score(touchpoints: List[PartnerTouchpoint], lookback_days: int) -> float:
    """Engagement score (0-25): Activity frequency."""
    if not touchpoints:
        return 5.0

    # Touchpoints per month
    months = lookback_days / 30
    touchpoints_per_month = len(touchpoints) / months if months > 0 else 0

    if touchpoints_per_month >= 12:  # Weekly+
        return 25.0
    elif touchpoints_per_month >= 6:  # Bi-weekly
        return 20.0
    elif touchpoints_per_month >= 3:  # Monthly
        return 15.0
    elif touchpoints_per_month >= 1:  # Quarterly
        return 10.0
    else:  # Rarely
        return 5.0


def _calculate_win_rate_score(
    partner_id: str,
    targets: List[AttributionTarget],
    touchpoints: List[PartnerTouchpoint]
) -> Optional[float]:
    """Win rate score (0-20): % of touched deals won. Returns None if no stage data."""
    win_rate = calculate_win_rate(partner_id, targets, touchpoints)

    if win_rate is None:
        return None  # No stage data available

    if win_rate >= 0.70:  # 70%+ win rate
        return 20.0
    elif win_rate >= 0.50:  # 50-70%
        return 15.0
    elif win_rate >= 0.30:  # 30-50%
        return 10.0
    else:  # <30%
        return 5.0


def _calculate_deal_size_score(ledger: List[LedgerEntry]) -> float:
    """Deal size score (0-10): Recent avg vs all-time avg."""
    if not ledger:
        return 5.0

    # All-time average
    all_time_avg = sum(e.attributed_value for e in ledger) / len(ledger)

    # Recent average (last 30 days)
    cutoff = datetime.now() - timedelta(days=30)
    recent_entries = [e for e in ledger if e.calculation_timestamp >= cutoff]

    if not recent_entries:
        return 5.0

    recent_avg = sum(e.attributed_value for e in recent_entries) / len(recent_entries)

    if recent_avg >= all_time_avg * 1.2:  # 20%+ larger
        return 10.0
    elif recent_avg >= all_time_avg:  # Same or larger
        return 8.0
    else:  # Declining
        return 5.0


def _calculate_consistency_score(touchpoints: List[PartnerTouchpoint]) -> float:
    """Consistency score (0-10): Standard deviation of days between touchpoints."""
    if len(touchpoints) < 2:
        return 5.0

    # Sort by timestamp
    sorted_tps = sorted([tp for tp in touchpoints if tp.timestamp], key=lambda tp: tp.timestamp)

    if len(sorted_tps) < 2:
        return 5.0

    # Calculate days between consecutive touchpoints
    gaps = []
    for i in range(1, len(sorted_tps)):
        gap = (sorted_tps[i].timestamp - sorted_tps[i-1].timestamp).days
        gaps.append(gap)

    # Standard deviation of gaps
    if gaps:
        std_days = statistics.stdev(gaps) if len(gaps) > 1 else gaps[0]

        if std_days <= 7:  # Very consistent (weekly)
            return 10.0
        elif std_days <= 14:  # Consistent (bi-weekly)
            return 8.0
        elif std_days <= 30:  # Somewhat regular
            return 6.0
        else:  # Sporadic
            return 3.0

    return 5.0


def _calculate_previous_health_score(
    partner_id: str,
    ledger: List[LedgerEntry],
    touchpoints: List[PartnerTouchpoint],
    targets: List[AttributionTarget],
    lookback_days: int
) -> Optional[float]:
    """Calculate health score for previous period (for trend comparison)."""
    # Shift time window back by lookback_days
    cutoff_start = datetime.now() - timedelta(days=lookback_days * 2)
    cutoff_end = datetime.now() - timedelta(days=lookback_days)

    prev_ledger = [e for e in ledger
                   if e.partner_id == partner_id
                   and cutoff_start <= e.calculation_timestamp < cutoff_end]

    if not prev_ledger:
        return None

    # Simplified calculation (just revenue trend for comparison)
    prev_revenue = sum(e.attributed_value for e in prev_ledger)

    # This is a simplified version - full calculation would be expensive
    # For trend purposes, just use revenue as proxy
    if prev_revenue > 0:
        return min(100, prev_revenue / 10000)  # Rough estimate

    return None


def _classify_health_grade(score: float) -> str:
    """Classify health score into letter grade."""
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


# ============================================================================
# Period Comparison
# ============================================================================

def calculate_period_comparison(
    ledger: List[LedgerEntry],
    targets: List[AttributionTarget],
    current_start: date,
    current_end: date,
    previous_start: date,
    previous_end: date
) -> PeriodComparison:
    """Compare current vs previous period metrics."""
    # Current period
    current_ledger = [
        e for e in ledger
        if current_start <= e.calculation_timestamp.date() <= current_end
    ]
    current_targets = [
        t for t in targets
        if current_start <= t.timestamp.date() <= current_end
    ]

    # Previous period
    previous_ledger = [
        e for e in ledger
        if previous_start <= e.calculation_timestamp.date() <= previous_end
    ]
    previous_targets = [
        t for t in targets
        if previous_start <= t.timestamp.date() <= previous_end
    ]

    # Calculate metrics
    current_revenue = sum(e.attributed_value for e in current_ledger)
    previous_revenue = sum(e.attributed_value for e in previous_ledger)

    if previous_revenue > 0:
        growth_pct = ((current_revenue - previous_revenue) / previous_revenue) * 100
    else:
        growth_pct = 100.0 if current_revenue > 0 else 0.0

    current_deals = len(set(e.target_id for e in current_ledger))
    previous_deals = len(set(e.target_id for e in previous_ledger))

    if previous_deals > 0:
        deal_growth_pct = ((current_deals - previous_deals) / previous_deals) * 100
    else:
        deal_growth_pct = 100.0 if current_deals > 0 else 0.0

    # Coverage
    current_total_revenue = sum(t.value for t in current_targets)
    previous_total_revenue = sum(t.value for t in previous_targets)

    current_coverage = (current_revenue / current_total_revenue * 100) if current_total_revenue > 0 else 0.0
    previous_coverage = (previous_revenue / previous_total_revenue * 100) if previous_total_revenue > 0 else 0.0

    return PeriodComparison(
        current_revenue=current_revenue,
        previous_revenue=previous_revenue,
        growth_percentage=growth_pct,
        current_deals=current_deals,
        previous_deals=previous_deals,
        deal_growth_percentage=deal_growth_pct,
        current_coverage=current_coverage,
        previous_coverage=previous_coverage
    )


def get_top_movers(
    ledger: List[LedgerEntry],
    partners: Dict[str, str],
    current_start: date,
    current_end: date,
    previous_start: date,
    previous_end: date
) -> List[PartnerChange]:
    """Get partners with biggest revenue changes."""
    partner_changes = []

    for partner_id, partner_name in partners.items():
        # Current period revenue
        current_revenue = sum(
            e.attributed_value for e in ledger
            if e.partner_id == partner_id
            and current_start <= e.calculation_timestamp.date() <= current_end
        )

        # Previous period revenue
        previous_revenue = sum(
            e.attributed_value for e in ledger
            if e.partner_id == partner_id
            and previous_start <= e.calculation_timestamp.date() <= previous_end
        )

        # Skip partners with no activity
        if current_revenue == 0 and previous_revenue == 0:
            continue

        # Calculate change
        change_amount = current_revenue - previous_revenue

        if previous_revenue > 0:
            change_pct = (change_amount / previous_revenue) * 100
        else:
            change_pct = 100.0 if current_revenue > 0 else 0.0

        # Trend indicator
        if change_pct >= 30:
            trend = "🚀"
        elif change_pct >= 10:
            trend = "↗"
        elif change_pct >= -10:
            trend = "→"
        else:
            trend = "↘"

        partner_changes.append(PartnerChange(
            partner_id=partner_id,
            partner_name=partner_name,
            current_revenue=current_revenue,
            previous_revenue=previous_revenue,
            change_amount=change_amount,
            change_percentage=change_pct,
            trend_indicator=trend
        ))

    # Sort by absolute change amount (descending)
    partner_changes.sort(key=lambda pc: abs(pc.change_amount), reverse=True)

    return partner_changes


# ============================================================================
# Alert Detection
# ============================================================================

def detect_alerts(
    targets: List[AttributionTarget],
    ledger: List[LedgerEntry],
    touchpoints: List[PartnerTouchpoint],
    partners: Dict[str, str],
    lookback_days: int = 30
) -> List[Alert]:
    """Detect actionable alerts for partner management."""
    alerts = []

    # Alert 1: Coverage Drop
    coverage_alert = _detect_coverage_alert(targets, ledger, lookback_days)
    if coverage_alert:
        alerts.append(coverage_alert)

    # Alert 2: Partner Disengagement
    disengagement_alerts = _detect_disengagement_alerts(touchpoints, partners, ledger, lookback_days)
    alerts.extend(disengagement_alerts)

    # Alert 3: Top Performers
    top_performer_alerts = _detect_top_performers(ledger, targets, touchpoints, partners, lookback_days)
    alerts.extend(top_performer_alerts)

    # Sort by severity and limit to top 5
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order[a.severity])

    return alerts[:5]  # Limit to 5 most important alerts


def _detect_coverage_alert(
    targets: List[AttributionTarget],
    ledger: List[LedgerEntry],
    lookback_days: int,
    threshold: float = 0.70
) -> Optional[Alert]:
    """Alert when attribution coverage < 70%."""
    cutoff = datetime.now() - timedelta(days=lookback_days)

    recent_targets = [t for t in targets if t.timestamp >= cutoff and t.metadata.get('is_closed', False)]
    recent_ledger = [e for e in ledger if e.calculation_timestamp >= cutoff]

    if not recent_targets:
        return None

    total_revenue = sum(t.value for t in recent_targets)
    attributed_revenue = sum(e.attributed_value for e in recent_ledger)

    coverage = attributed_revenue / total_revenue if total_revenue > 0 else 0

    if coverage < threshold:
        return Alert(
            severity="warning",
            title="Attribution Coverage Below Target",
            description=f"Partner touchpoint attribution at {coverage:.1%} of closed deals (target: {threshold:.0%}) - gap of ${(total_revenue - attributed_revenue):,.0f}",
            partner_id=None,
            partner_name=None,
            recommended_action="Audit recent high-value opportunities to ensure partner engagement is properly captured in CRM",
            timestamp=datetime.now()
        )

    return None


def _detect_disengagement_alerts(
    touchpoints: List[PartnerTouchpoint],
    partners: Dict[str, str],
    ledger: List[LedgerEntry],
    lookback_days: int,
    threshold_days: int = 14
) -> List[Alert]:
    """Alert when active partner has no touchpoints in 14+ days."""
    alerts = []
    cutoff_90d = datetime.now() - timedelta(days=90)

    # Find active partners (>$50K last quarter)
    partner_revenue_90d = {}
    for entry in ledger:
        if entry.calculation_timestamp >= cutoff_90d:
            partner_revenue_90d[entry.partner_id] = partner_revenue_90d.get(entry.partner_id, 0) + entry.attributed_value

    active_partners = {pid: rev for pid, rev in partner_revenue_90d.items() if rev > 50000}

    # Check last touchpoint for each active partner
    for partner_id, revenue in active_partners.items():
        partner_tps = [tp for tp in touchpoints if tp.partner_id == partner_id and tp.timestamp]

        if not partner_tps:
            continue

        last_tp = max(partner_tps, key=lambda tp: tp.timestamp)
        days_since = (datetime.now() - last_tp.timestamp).days

        if days_since >= threshold_days:
            partner_name = partners.get(partner_id, partner_id)
            alerts.append(Alert(
                severity="warning",
                title="Partner Disengagement Risk",
                description=f"{partner_name}: No touchpoint activity in {days_since} days - below normal engagement cadence",
                partner_id=partner_id,
                partner_name=partner_name,
                recommended_action="Proactive outreach recommended to re-engage partner account team",
                timestamp=datetime.now()
            ))

    return alerts[:2]  # Limit to 2 disengagement alerts


def _detect_top_performers(
    ledger: List[LedgerEntry],
    targets: List[AttributionTarget],
    touchpoints: List[PartnerTouchpoint],
    partners: Dict[str, str],
    lookback_days: int
) -> List[Alert]:
    """Alert for partners with >20% growth and >60% win rate."""
    alerts = []
    cutoff = datetime.now() - timedelta(days=lookback_days)
    prev_cutoff = datetime.now() - timedelta(days=lookback_days * 2)

    for partner_id, partner_name in partners.items():
        # Current period revenue
        current_revenue = sum(
            e.attributed_value for e in ledger
            if e.partner_id == partner_id and e.calculation_timestamp >= cutoff
        )

        # Previous period revenue
        previous_revenue = sum(
            e.attributed_value for e in ledger
            if e.partner_id == partner_id
            and prev_cutoff <= e.calculation_timestamp < cutoff
        )

        if previous_revenue == 0 or current_revenue < 10000:
            continue

        growth = (current_revenue - previous_revenue) / previous_revenue
        win_rate = calculate_win_rate(partner_id, targets, touchpoints)

        if growth >= 0.20 and (win_rate is None or win_rate >= 0.60):
            alerts.append(Alert(
                severity="info",
                title="High-Performing Partner",
                description=f"{partner_name}: Strong performance with +{growth*100:.0f}% attributed revenue growth" + (f" and {win_rate:.0%} close rate" if win_rate else ""),
                partner_id=partner_id,
                partner_name=partner_name,
                recommended_action="Opportunity to deepen partnership investment and expand co-selling motion",
                timestamp=datetime.now()
            ))

    return alerts[:1]  # Limit to 1 top performer alert


# ============================================================================
# Win Rate & Deal Velocity
# ============================================================================

def calculate_win_rate(
    partner_id: str,
    targets: List[AttributionTarget],
    touchpoints: List[PartnerTouchpoint]
) -> Optional[float]:
    """
    Calculate partner's win rate (% of touched deals won).

    Returns None if no stage data available.
    """
    # Find all targets this partner touched
    partner_target_ids = {tp.target_id for tp in touchpoints if tp.partner_id == partner_id}

    if not partner_target_ids:
        return None

    # Count won vs total closed deals
    total_closed = 0
    won_deals = 0

    for target in targets:
        if target.id not in partner_target_ids:
            continue

        stage = target.metadata.get('stage')
        is_closed = target.metadata.get('is_closed', False)
        is_won = target.metadata.get('is_won', False)

        # Skip if no stage data or not closed
        if not stage or not is_closed:
            continue

        total_closed += 1
        if is_won:
            won_deals += 1

    if total_closed == 0:
        return None  # No closed deals with stage data

    return won_deals / total_closed


def calculate_deal_velocity(
    partner_id: str,
    targets: List[AttributionTarget],
    touchpoints: List[PartnerTouchpoint]
) -> Optional[float]:
    """
    Calculate average days from partner's first touch to deal close.

    Returns None if no created_date or timestamp data available.
    """
    # Find targets where this partner was involved
    partner_target_ids = {tp.target_id for tp in touchpoints if tp.partner_id == partner_id}

    velocities = []

    for target in targets:
        if target.id not in partner_target_ids:
            continue

        # Get created_date and close date
        created_date_str = target.metadata.get('created_date')
        close_date = target.timestamp

        if not created_date_str or not close_date:
            continue

        # Parse created_date (ISO format string)
        try:
            from dateutil import parser
            created_date = parser.parse(created_date_str)
        except:
            try:
                created_date = datetime.fromisoformat(created_date_str)
            except:
                continue

        # Calculate days
        days = (close_date - created_date).days

        if days > 0:
            velocities.append(days)

    if not velocities:
        return None

    return sum(velocities) / len(velocities)


# ============================================================================
# Partner Insights
# ============================================================================

def generate_partner_insights(
    partner_id: str,
    health_score: HealthScore,
    metrics: Dict[str, Any]
) -> PartnerInsights:
    """Generate strengths, improvements, and recommendations."""
    strengths = []
    improvements = []
    recommendations = []

    revenue_growth = metrics.get('revenue_growth', 0)
    win_rate = metrics.get('win_rate')
    avg_deal = metrics.get('avg_deal_size', 0)
    velocity = metrics.get('deal_velocity')

    # Analyze revenue trend
    if health_score.revenue_trend_score >= 30:
        if revenue_growth >= 50:
            strengths.append(f"Exceptional pipeline growth at {revenue_growth:.0f}% QoQ - momentum accelerating")
        elif revenue_growth >= 20:
            strengths.append(f"Strong attributed revenue growth at {revenue_growth:.0f}% quarter-over-quarter")
        else:
            strengths.append(f"Positive revenue trajectory with {revenue_growth:.0f}% growth")
    elif health_score.revenue_trend_score < 20:
        if revenue_growth < -20:
            improvements.append(f"Significant revenue decline at {revenue_growth:.0f}% QoQ - immediate attention needed")
            recommendations.append("Schedule executive alignment meeting to review partnership KPIs and joint GTM strategy")
        else:
            improvements.append(f"Revenue contraction of {revenue_growth:.0f}% QoQ")
            recommendations.append("Review recent deal flow and identify blockers in sales cycle")

    # Analyze win rate
    if win_rate is not None:
        baseline = 0.45
        if win_rate >= 0.70:
            strengths.append(f"Excellent close rate at {win_rate:.0%} - significantly outperforming peer average")
        elif win_rate >= 0.50:
            strengths.append(f"Solid win rate at {win_rate:.0%} on influenced opportunities")
        elif win_rate < 0.30:
            improvements.append(f"Win rate of {win_rate:.0%} below target threshold")
            recommendations.append("Conduct deal retrospective on recent losses to identify common patterns and objections")

    # Analyze engagement
    if health_score.engagement_score >= 20:
        strengths.append("Consistent touchpoint cadence with regular deal engagement")
    elif health_score.engagement_score < 15:
        improvements.append("Touchpoint frequency has decreased in recent weeks")
        recommendations.append("Re-establish weekly pipeline review cadence with partner account team")

    # Analyze deal size
    if avg_deal > 75000:
        strengths.append(f"Strong enterprise focus with ${avg_deal/1000:.0f}K average deal value")
    elif avg_deal > 50000:
        strengths.append(f"Solid mid-market presence at ${avg_deal/1000:.0f}K average deal size")
    elif health_score.deal_size_score < 8 and avg_deal > 0:
        improvements.append("Average deal size trending downward compared to historical baseline")
        recommendations.append("Explore opportunities to move upmarket or expand existing customer footprint")

    # Analyze velocity
    if velocity:
        if velocity < 35:
            strengths.append(f"Efficient sales cycle averaging {velocity:.0f} days from first touch to close")
        elif velocity > 70:
            improvements.append(f"Extended sales cycles at {velocity:.0f} days - longer than benchmark")
            recommendations.append("Identify friction points in deal progression and streamline approval workflows")
        elif velocity > 50:
            improvements.append(f"Deal velocity at {velocity:.0f} days has room for optimization")

    # Ensure we have content
    if not strengths:
        strengths.append("Partner maintains active involvement in pipeline opportunities")

    if not improvements and health_score.overall_score >= 80:
        strengths.append("Partner health metrics tracking well across all dimensions")

    if not recommendations:
        if health_score.overall_score >= 80:
            recommendations.append("Maintain current engagement model and explore expansion into adjacent verticals")
        else:
            recommendations.append("Schedule monthly business review to align on pipeline targets and enablement needs")

    return PartnerInsights(
        strengths=strengths,
        improvements=improvements,
        recommendations=recommendations
    )
