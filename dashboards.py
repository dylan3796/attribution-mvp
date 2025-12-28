"""
Dashboard and visualization components for Attribution MVP.
Includes charts, metrics, and analytics visualizations.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
from typing import Optional, Tuple
import streamlit as st


def create_revenue_over_time_chart(revenue_df: pd.DataFrame) -> go.Figure:
    """
    Create a line chart showing revenue over time.

    Args:
        revenue_df: DataFrame with columns: revenue_date, amount, account_id (optional)

    Returns:
        Plotly figure object
    """
    if revenue_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No revenue data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Group by date
    daily_revenue = revenue_df.groupby('revenue_date')['amount'].sum().reset_index()
    daily_revenue['revenue_date'] = pd.to_datetime(daily_revenue['revenue_date'])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_revenue['revenue_date'],
        y=daily_revenue['amount'],
        mode='lines+markers',
        name='Daily Revenue',
        line=dict(color='#3b82f6', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)'
    ))

    fig.update_layout(
        title="Revenue Over Time",
        xaxis_title="Date",
        yaxis_title="Revenue ($)",
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )

    return fig


def create_partner_performance_bar_chart(partner_df: pd.DataFrame) -> go.Figure:
    """
    Create a horizontal bar chart showing partner performance.

    Args:
        partner_df: DataFrame with columns: partner_name, attributed_amount

    Returns:
        Plotly figure object
    """
    if partner_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No partner attribution data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Sort by revenue
    partner_df = partner_df.sort_values('attributed_amount', ascending=True)

    # Color gradient based on revenue
    colors = px.colors.sequential.Blues[::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=partner_df['attributed_amount'],
        y=partner_df['partner_name'],
        orientation='h',
        marker=dict(
            color=partner_df['attributed_amount'],
            colorscale=colors,
            showscale=False
        ),
        text=partner_df['attributed_amount'].apply(lambda x: f"${x:,.0f}"),
        textposition='outside'
    ))

    fig.update_layout(
        title="Partner Performance Leaderboard",
        xaxis_title="Attributed Revenue ($)",
        yaxis_title="",
        template='plotly_white',
        height=max(300, len(partner_df) * 40),
        margin=dict(l=150, r=50, t=50, b=50)
    )

    return fig


def create_attribution_pie_chart(attribution_df: pd.DataFrame) -> go.Figure:
    """
    Create a pie chart showing attribution distribution by partner.

    Args:
        attribution_df: DataFrame with columns: partner_name, attributed_amount

    Returns:
        Plotly figure object
    """
    if attribution_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No attribution data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    fig = go.Figure(data=[go.Pie(
        labels=attribution_df['partner_name'],
        values=attribution_df['attributed_amount'],
        hole=0.4,
        marker=dict(
            colors=px.colors.qualitative.Set3
        ),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
    )])

    fig.update_layout(
        title="Attribution Distribution",
        template='plotly_white',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        )
    )

    return fig


def create_pipeline_funnel_chart(use_cases_df: pd.DataFrame) -> go.Figure:
    """
    Create a funnel chart showing pipeline value by stage.

    Args:
        use_cases_df: DataFrame with columns: stage, estimated_value

    Returns:
        Plotly figure object
    """
    if use_cases_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No pipeline data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Define stage order
    stage_order = ['Discovery', 'Evaluation', 'Commit', 'Live']

    # Group by stage and sum estimated values
    pipeline = use_cases_df.groupby('stage')['estimated_value'].sum().reset_index()

    # Ensure all stages are present
    all_stages = pd.DataFrame({'stage': stage_order})
    pipeline = all_stages.merge(pipeline, on='stage', how='left').fillna(0)

    fig = go.Figure(go.Funnel(
        y=pipeline['stage'],
        x=pipeline['estimated_value'],
        textinfo="value+percent initial",
        marker=dict(
            color=['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'],
        ),
        texttemplate='$%{value:,.0f}<br>%{percentInitial}'
    ))

    fig.update_layout(
        title="Pipeline Value Funnel",
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )

    return fig


def create_account_health_gauge(
    revenue_last_30d: float,
    revenue_last_60d: float,
    active_use_cases: int,
    total_partners: int
) -> go.Figure:
    """
    Create a gauge chart showing account health score.

    Args:
        revenue_last_30d: Revenue in last 30 days
        revenue_last_60d: Revenue in last 60 days
        active_use_cases: Number of active use cases
        total_partners: Number of partners engaged

    Returns:
        Plotly figure object
    """
    # Calculate health score (0-100)
    score = 0

    # Revenue trend (40 points)
    if revenue_last_60d > 0:
        revenue_growth = ((revenue_last_30d - (revenue_last_60d - revenue_last_30d)) /
                         (revenue_last_60d - revenue_last_30d)) if revenue_last_60d > revenue_last_30d else 0
        score += min(40, max(0, revenue_growth * 20 + 20))
    elif revenue_last_30d > 0:
        score += 20

    # Active use cases (30 points)
    score += min(30, active_use_cases * 5)

    # Partner engagement (30 points)
    score += min(30, total_partners * 6)

    # Determine color
    if score >= 70:
        color = "#10b981"  # green
    elif score >= 40:
        color = "#f59e0b"  # orange
    else:
        color = "#ef4444"  # red

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Account Health Score"},
        delta={'reference': 70, 'increasing': {'color': "#10b981"}},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 40], 'color': "#fee2e2"},
                {'range': [40, 70], 'color': "#fef3c7"},
                {'range': [70, 100], 'color': "#d1fae5"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    return fig


def create_attribution_waterfall(attribution_df: pd.DataFrame, total_revenue: float) -> go.Figure:
    """
    Create a waterfall chart showing attribution breakdown.

    Args:
        attribution_df: DataFrame with columns: partner_name, attributed_amount
        total_revenue: Total revenue for the period

    Returns:
        Plotly figure object
    """
    if attribution_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No attribution data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Sort by attributed amount
    attribution_df = attribution_df.sort_values('attributed_amount', ascending=False)

    # Calculate unattributed
    total_attributed = attribution_df['attributed_amount'].sum()
    unattributed = max(0, total_revenue - total_attributed)

    # Build waterfall data
    x = ['Total Revenue'] + list(attribution_df['partner_name']) + ['Unattributed', 'Reconciled']
    measure = ['absolute'] + ['relative'] * len(attribution_df) + ['relative', 'total']
    y = [total_revenue] + list(-attribution_df['attributed_amount']) + [-unattributed, total_revenue]

    fig = go.Figure(go.Waterfall(
        x=x,
        measure=measure,
        y=y,
        text=[f"${val:,.0f}" for val in y],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#3b82f6"}},
        increasing={"marker": {"color": "#10b981"}},
        totals={"marker": {"color": "#8b5cf6"}}
    ))

    fig.update_layout(
        title="Revenue Attribution Waterfall",
        yaxis_title="Revenue ($)",
        template='plotly_white',
        height=500,
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=100)
    )

    return fig


def create_revenue_trend_sparkline(revenue_df: pd.DataFrame, days: int = 30) -> go.Figure:
    """
    Create a small sparkline chart for revenue trend.

    Args:
        revenue_df: DataFrame with columns: revenue_date, amount
        days: Number of days to show

    Returns:
        Plotly figure object
    """
    if revenue_df.empty:
        return go.Figure()

    # Filter to last N days
    end_date = pd.to_datetime(revenue_df['revenue_date'].max())
    start_date = end_date - timedelta(days=days)

    filtered = revenue_df[pd.to_datetime(revenue_df['revenue_date']) >= start_date]
    daily = filtered.groupby('revenue_date')['amount'].sum().reset_index()
    daily['revenue_date'] = pd.to_datetime(daily['revenue_date'])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily['revenue_date'],
        y=daily['amount'],
        mode='lines',
        line=dict(color='#3b82f6', width=2),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))

    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        height=80,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig


def create_partner_role_distribution(use_case_partners_df: pd.DataFrame) -> go.Figure:
    """
    Create a donut chart showing distribution of partner roles.

    Args:
        use_case_partners_df: DataFrame with columns: partner_role

    Returns:
        Plotly figure object
    """
    if use_case_partners_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No partner roles assigned",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    role_counts = use_case_partners_df['partner_role'].value_counts().reset_index()
    role_counts.columns = ['role', 'count']

    fig = go.Figure(data=[go.Pie(
        labels=role_counts['role'],
        values=role_counts['count'],
        hole=0.5,
        marker=dict(
            colors=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']
        ),
        textinfo='label+value',
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>'
    )])

    fig.update_layout(
        title="Partner Role Distribution",
        template='plotly_white',
        height=350,
        showlegend=False
    )

    return fig
