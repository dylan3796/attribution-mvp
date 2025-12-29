"""
Partner Dashboard Visualizations
==================================

Plotly visualizations for partner management dashboards.

Provides:
- Health score gauge charts
- Period comparison charts
- Deal velocity visualizations
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any

from partner_analytics import PeriodComparison, PartnerChange
from utils_partner import get_health_color


# ============================================================================
# Health Score Visualizations
# ============================================================================

def create_health_gauge(
    score: float,
    title: str = "Partner Health Score",
    show_grade: bool = True
) -> go.Figure:
    """
    Create gauge chart for partner health score.

    Args:
        score: Health score (0-100)
        title: Chart title
        show_grade: Include letter grade in display

    Returns:
        Plotly figure
    """
    # Determine color based on score
    if score >= 70:
        color = "#10b981"  # Green
        bar_color = "green"
    elif score >= 40:
        color = "#f59e0b"  # Orange/Yellow
        bar_color = "yellow"
    else:
        color = "#ef4444"  # Red
        bar_color = "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text': title, 'font': {'size': 20}},
        number={'suffix': "/100", 'font': {'size': 36}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': '#fee2e2'},  # Light red
                {'range': [40, 70], 'color': '#fef3c7'},  # Light yellow
                {'range': [70, 100], 'color': '#d1fae5'}  # Light green
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
        template='plotly_white'
    )

    return fig


def create_health_score_breakdown(
    revenue_score: float,
    engagement_score: float,
    win_rate_score: float,
    deal_size_score: float,
    consistency_score: float
) -> go.Figure:
    """
    Create horizontal bar chart showing health score component breakdown.

    Args:
        revenue_score: Revenue trend score (0-35)
        engagement_score: Engagement level score (0-25)
        win_rate_score: Win rate score (0-20, can be None)
        deal_size_score: Deal size trend score (0-10)
        consistency_score: Consistency score (0-10)

    Returns:
        Plotly figure
    """
    components = []
    scores = []
    max_scores = []
    colors = []

    # Revenue Trend
    components.append("Revenue Trend")
    scores.append(revenue_score)
    max_scores.append(35)
    colors.append('#3b82f6')  # Blue

    # Engagement
    components.append("Engagement Level")
    scores.append(engagement_score)
    max_scores.append(25)
    colors.append('#10b981')  # Green

    # Win Rate (optional)
    if win_rate_score is not None:
        components.append("Win Rate")
        scores.append(win_rate_score)
        max_scores.append(20)
        colors.append('#8b5cf6')  # Purple

    # Deal Size
    components.append("Deal Size Trend")
    scores.append(deal_size_score)
    max_scores.append(10)
    colors.append('#f59e0b')  # Orange

    # Consistency
    components.append("Consistency")
    scores.append(consistency_score)
    max_scores.append(10)
    colors.append('#06b6d4')  # Cyan

    fig = go.Figure()

    # Add bars
    fig.add_trace(go.Bar(
        y=components,
        x=scores,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{score}/{max_score}" for score, max_score in zip(scores, max_scores)],
        textposition='inside',
        textfont=dict(color='white', size=12),
        hovertemplate='<b>%{y}</b><br>Score: %{x}<extra></extra>'
    ))

    fig.update_layout(
        title="Health Score Components",
        xaxis_title="Score",
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        template='plotly_white',
        showlegend=False
    )

    fig.update_xaxis(range=[0, max(max_scores)])

    return fig


# ============================================================================
# Period Comparison Visualizations
# ============================================================================

def create_period_comparison_chart(
    comparison: PeriodComparison,
    metric_type: str = "revenue"
) -> go.Figure:
    """
    Create grouped bar chart comparing current vs previous period.

    Args:
        comparison: PeriodComparison object
        metric_type: "revenue" or "deals"

    Returns:
        Plotly figure
    """
    if metric_type == "revenue":
        current_value = comparison.current_revenue
        previous_value = comparison.previous_revenue
        title = "Revenue: Current vs Previous Period"
        y_axis_title = "Revenue ($)"
        value_format = "$.2s"
    else:  # deals
        current_value = comparison.current_deals
        previous_value = comparison.previous_deals
        title = "Deals: Current vs Previous Period"
        y_axis_title = "Number of Deals"
        value_format = "d"

    fig = go.Figure()

    # Previous period bar
    fig.add_trace(go.Bar(
        name='Previous Period',
        x=['Period Comparison'],
        y=[previous_value],
        marker_color='#94a3b8',  # Gray
        text=[f"${previous_value:,.0f}" if metric_type == "revenue" else f"{previous_value}"],
        textposition='auto',
        hovertemplate=f'<b>Previous</b><br>Value: %{{y:{value_format}}}<extra></extra>'
    ))

    # Current period bar
    fig.add_trace(go.Bar(
        name='Current Period',
        x=['Period Comparison'],
        y=[current_value],
        marker_color='#3b82f6',  # Blue
        text=[f"${current_value:,.0f}" if metric_type == "revenue" else f"{current_value}"],
        textposition='auto',
        hovertemplate=f'<b>Current</b><br>Value: %{{y:{value_format}}}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        yaxis_title=y_axis_title,
        barmode='group',
        height=400,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=80, b=50)
    )

    return fig


def create_top_movers_chart(movers: List[PartnerChange], limit: int = 10) -> go.Figure:
    """
    Create bar chart showing top revenue movers (gainers and losers).

    Args:
        movers: List of PartnerChange objects
        limit: Number of partners to show

    Returns:
        Plotly figure
    """
    if not movers:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Take top N by absolute change
    top_movers = movers[:limit]

    # Prepare data
    names = [m.partner_name for m in top_movers]
    changes = [m.change_amount for m in top_movers]
    percentages = [m.change_percentage for m in top_movers]
    colors = ['#10b981' if c > 0 else '#ef4444' for c in changes]  # Green for gain, red for loss

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=names,
        x=changes,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{pct:+.0f}%" for pct in percentages],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Change: $%{x:,.0f}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title="Top Revenue Movers",
        xaxis_title="Revenue Change ($)",
        height=max(300, len(top_movers) * 40),
        template='plotly_white',
        margin=dict(l=150, r=50, t=50, b=50),
        showlegend=False
    )

    return fig


# ============================================================================
# Deal Velocity & Engagement Visualizations
# ============================================================================

def create_deal_velocity_chart(velocity_data: List[Dict[str, Any]]) -> go.Figure:
    """
    Create box plot or bar chart showing deal velocity distribution.

    Args:
        velocity_data: List of dicts with 'partner_name' and 'days' keys

    Returns:
        Plotly figure
    """
    if not velocity_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No velocity data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Create box plot
    fig = go.Figure()

    fig.add_trace(go.Box(
        y=[d['days'] for d in velocity_data],
        name='Deal Velocity',
        marker_color='#3b82f6',
        boxmean='sd',  # Show mean and standard deviation
        hovertemplate='<b>Days to Close</b><br>%{y} days<extra></extra>'
    ))

    fig.update_layout(
        title="Deal Velocity Distribution",
        yaxis_title="Days to Close",
        height=400,
        template='plotly_white',
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=False
    )

    return fig


def create_partner_revenue_trend(
    partner_name: str,
    trend_data: pd.DataFrame
) -> go.Figure:
    """
    Create line chart showing partner's revenue trend over time.

    Args:
        partner_name: Partner name for title
        trend_data: DataFrame with 'month' and 'revenue' columns

    Returns:
        Plotly figure
    """
    if trend_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No revenue data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=trend_data['month'],
        y=trend_data['revenue'],
        mode='lines+markers',
        name='Revenue',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=8, color='#3b82f6'),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)',
        hovertemplate='<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=f"{partner_name} - Revenue Trend (12 Months)",
        xaxis_title="Month",
        yaxis_title="Attributed Revenue ($)",
        height=350,
        template='plotly_white',
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=False
    )

    return fig


def create_partner_activity_trend(
    partner_name: str,
    activity_data: pd.DataFrame
) -> go.Figure:
    """
    Create bar chart showing partner's activity (touchpoints) over time.

    Args:
        partner_name: Partner name for title
        activity_data: DataFrame with 'month' and 'touchpoints' columns

    Returns:
        Plotly figure
    """
    if activity_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No activity data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=activity_data['month'],
        y=activity_data['touchpoints'],
        marker_color='#10b981',
        hovertemplate='<b>%{x}</b><br>Touchpoints: %{y}<extra></extra>'
    ))

    fig.update_layout(
        title=f"{partner_name} - Engagement Activity",
        xaxis_title="Month",
        yaxis_title="Number of Touchpoints",
        height=350,
        template='plotly_white',
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=False
    )

    return fig


# ============================================================================
# Alert Visualizations
# ============================================================================

def create_alert_timeline(alerts: List[Dict[str, Any]]) -> go.Figure:
    """
    Create timeline visualization of alerts.

    Args:
        alerts: List of alert dictionaries with 'timestamp', 'severity', 'title' keys

    Returns:
        Plotly figure
    """
    if not alerts:
        fig = go.Figure()
        fig.add_annotation(
            text="No alerts",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Sort by timestamp
    alerts_sorted = sorted(alerts, key=lambda a: a['timestamp'])

    # Color by severity
    severity_colors = {
        'critical': '#ef4444',  # Red
        'warning': '#f59e0b',   # Orange
        'info': '#3b82f6'       # Blue
    }

    colors = [severity_colors.get(a['severity'], '#94a3b8') for a in alerts_sorted]
    timestamps = [a['timestamp'] for a in alerts_sorted]
    titles = [a['title'] for a in alerts_sorted]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=[1] * len(timestamps),  # All on same horizontal line
        mode='markers+text',
        marker=dict(size=15, color=colors, symbol='circle'),
        text=titles,
        textposition="top center",
        hovertemplate='<b>%{text}</b><br>%{x}<extra></extra>'
    ))

    fig.update_layout(
        title="Alert Timeline",
        xaxis_title="Date",
        height=300,
        template='plotly_white',
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=False,
        yaxis=dict(visible=False)
    )

    return fig
