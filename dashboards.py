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


def create_deal_value_distribution(revenue_df: pd.DataFrame) -> go.Figure:
    """
    Create a histogram showing deal value distribution with size segments.

    Args:
        revenue_df: DataFrame with columns: amount, deal_type (optional)

    Returns:
        Plotly figure object
    """
    if revenue_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No deal data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Define deal size segments
    def categorize_deal_size(amount):
        if amount < 25000:
            return "SMB ($0-$25K)"
        elif amount < 100000:
            return "Mid-Market ($25K-$100K)"
        elif amount < 500000:
            return "Enterprise ($100K-$500K)"
        else:
            return "Strategic ($500K+)"

    revenue_df['deal_segment'] = revenue_df['amount'].apply(categorize_deal_size)

    # Count and sum by segment
    segment_stats = revenue_df.groupby('deal_segment').agg({
        'amount': ['sum', 'count']
    }).reset_index()
    segment_stats.columns = ['segment', 'total_value', 'count']

    # Order segments
    segment_order = ["SMB ($0-$25K)", "Mid-Market ($25K-$100K)", "Enterprise ($100K-$500K)", "Strategic ($500K+)"]
    segment_stats['segment'] = pd.Categorical(segment_stats['segment'], categories=segment_order, ordered=True)
    segment_stats = segment_stats.sort_values('segment')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Total Value',
        x=segment_stats['segment'],
        y=segment_stats['total_value'],
        text=[f"${v:,.0f}" for v in segment_stats['total_value']],
        textposition='outside',
        marker_color=['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'],
        hovertemplate='<b>%{x}</b><br>Total Value: $%{y:,.0f}<br><extra></extra>'
    ))

    fig.update_layout(
        title="Deal Value Distribution by Size Segment",
        xaxis_title="Deal Size Segment",
        yaxis_title="Total Value ($)",
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        showlegend=False
    )

    return fig


# Keep old function for backwards compatibility but mark as deprecated
def create_pipeline_funnel_chart(use_cases_df: pd.DataFrame) -> go.Figure:
    """
    DEPRECATED: Use create_deal_value_distribution instead.

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


# ============================================================================
# REVENUE RELATIONSHIPS DASHBOARD
# ============================================================================

def create_revenue_by_actor_type_chart(touchpoints_df: pd.DataFrame, ledger_df: pd.DataFrame) -> go.Figure:
    """
    Create a bar chart showing attributed revenue by actor type.

    Args:
        touchpoints_df: DataFrame with columns: actor_type, actor_id, target_id
        ledger_df: DataFrame with columns: target_id, attributed_value

    Returns:
        Plotly figure object
    """
    if touchpoints_df.empty or ledger_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No attribution data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Merge touchpoints with ledger to get attributed values by actor type
    merged = touchpoints_df.merge(ledger_df, on='target_id', how='inner')
    by_actor_type = merged.groupby('actor_type')['attributed_value'].sum().reset_index()
    by_actor_type = by_actor_type.sort_values('attributed_value', ascending=True)

    # Color mapping for actor types
    color_map = {
        'partner': '#3b82f6',
        'campaign': '#10b981',
        'sales_rep': '#f59e0b',
        'channel': '#8b5cf6',
        'customer_referral': '#ec4899',
        'event': '#06b6d4',
        'content': '#84cc16',
        'custom': '#6b7280'
    }

    colors = [color_map.get(t, '#6b7280') for t in by_actor_type['actor_type']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=by_actor_type['attributed_value'],
        y=by_actor_type['actor_type'].str.replace('_', ' ').str.title(),
        orientation='h',
        marker=dict(color=colors),
        text=by_actor_type['attributed_value'].apply(lambda x: f"${x:,.0f}"),
        textposition='outside'
    ))

    fig.update_layout(
        title="Attributed Revenue by Contributor Type",
        xaxis_title="Attributed Revenue ($)",
        yaxis_title="",
        template='plotly_white',
        height=max(300, len(by_actor_type) * 50),
        margin=dict(l=150, r=80, t=50, b=50)
    )

    return fig


def create_revenue_by_type_chart(targets_df: pd.DataFrame) -> go.Figure:
    """
    Create a donut chart showing revenue distribution by revenue type.

    Args:
        targets_df: DataFrame with columns: revenue_type, value

    Returns:
        Plotly figure object
    """
    if targets_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No revenue data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Filter out null revenue types and group
    df = targets_df[targets_df['revenue_type'].notna()].copy()
    if df.empty:
        df = targets_df.copy()
        df['revenue_type'] = 'Unclassified'

    by_rev_type = df.groupby('revenue_type')['value'].sum().reset_index()

    # Color mapping for revenue types
    color_map = {
        'new_logo': '#10b981',      # Green - new business
        'expansion': '#3b82f6',     # Blue - growth
        'renewal': '#8b5cf6',       # Purple - retention
        'services': '#f59e0b',      # Orange - services
        'consumption': '#06b6d4',   # Cyan - usage
        'custom': '#6b7280',        # Gray - custom
        'Unclassified': '#d1d5db'   # Light gray
    }

    colors = [color_map.get(t, '#6b7280') for t in by_rev_type['revenue_type']]

    fig = go.Figure(data=[go.Pie(
        labels=by_rev_type['revenue_type'].str.replace('_', ' ').str.title(),
        values=by_rev_type['value'],
        hole=0.45,
        marker=dict(colors=colors),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
    )])

    fig.update_layout(
        title="Revenue by Type",
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


def create_actor_contribution_trend(touchpoints_df: pd.DataFrame, ledger_df: pd.DataFrame) -> go.Figure:
    """
    Create a stacked area chart showing actor contribution over time.

    Args:
        touchpoints_df: DataFrame with columns: actor_type, target_id, timestamp
        ledger_df: DataFrame with columns: target_id, attributed_value, calculation_timestamp

    Returns:
        Plotly figure object
    """
    if touchpoints_df.empty or ledger_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No trend data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Merge and prepare time series
    merged = touchpoints_df.merge(ledger_df, on='target_id', how='inner')

    # Use calculation_timestamp or timestamp
    if 'calculation_timestamp' in merged.columns:
        merged['date'] = pd.to_datetime(merged['calculation_timestamp']).dt.date
    elif 'timestamp' in merged.columns:
        merged['date'] = pd.to_datetime(merged['timestamp']).dt.date
    else:
        fig = go.Figure()
        fig.add_annotation(text="No timestamp data", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    # Group by date and actor type
    trend = merged.groupby(['date', 'actor_type'])['attributed_value'].sum().reset_index()
    trend_pivot = trend.pivot(index='date', columns='actor_type', values='attributed_value').fillna(0)

    # Color mapping
    color_map = {
        'partner': '#3b82f6',
        'campaign': '#10b981',
        'sales_rep': '#f59e0b',
        'channel': '#8b5cf6',
        'customer_referral': '#ec4899',
        'event': '#06b6d4',
        'content': '#84cc16',
        'custom': '#6b7280'
    }

    fig = go.Figure()
    for col in trend_pivot.columns:
        fig.add_trace(go.Scatter(
            x=trend_pivot.index,
            y=trend_pivot[col],
            mode='lines',
            name=col.replace('_', ' ').title(),
            stackgroup='one',
            line=dict(color=color_map.get(col, '#6b7280')),
            hovertemplate=f'<b>{col.replace("_", " ").title()}</b><br>' +
                          'Date: %{x}<br>Revenue: $%{y:,.0f}<extra></extra>'
        ))

    fig.update_layout(
        title="Attribution Contribution Over Time",
        xaxis_title="Date",
        yaxis_title="Attributed Revenue ($)",
        template='plotly_white',
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_revenue_relationship_sankey(
    touchpoints_df: pd.DataFrame,
    targets_df: pd.DataFrame,
    ledger_df: pd.DataFrame
) -> go.Figure:
    """
    Create a Sankey diagram showing revenue flow from actors through targets.

    Args:
        touchpoints_df: DataFrame with columns: actor_type, actor_name, target_id
        targets_df: DataFrame with columns: id, name, revenue_type, value
        ledger_df: DataFrame with columns: target_id, attributed_value

    Returns:
        Plotly Sankey figure
    """
    if touchpoints_df.empty or targets_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No relationship data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Limit to top actors for readability
    top_actors = touchpoints_df.groupby(['actor_type', 'actor_id', 'actor_name']).size().reset_index(name='count')
    top_actors = top_actors.nlargest(10, 'count')

    # Prepare nodes: Actor Types -> Actors -> Revenue Types
    actor_types = touchpoints_df['actor_type'].unique().tolist()
    actor_names = top_actors['actor_name'].fillna(top_actors['actor_id']).unique().tolist()
    rev_types = targets_df['revenue_type'].dropna().unique().tolist()
    if not rev_types:
        rev_types = ['Revenue']

    # Build node list
    nodes = actor_types + actor_names + rev_types
    node_indices = {name: i for i, name in enumerate(nodes)}

    # Build links
    sources = []
    targets_list = []
    values = []
    colors = []

    # Actor type -> Actor name links
    for _, row in top_actors.iterrows():
        actor_name = row['actor_name'] or row['actor_id']
        if row['actor_type'] in node_indices and actor_name in node_indices:
            sources.append(node_indices[row['actor_type']])
            targets_list.append(node_indices[actor_name])
            values.append(row['count'])
            colors.append('rgba(59, 130, 246, 0.4)')

    # Actor name -> Revenue type links (via touchpoints and targets)
    merged = touchpoints_df.merge(targets_df, left_on='target_id', right_on='id', how='inner')
    merged = merged.merge(ledger_df[['target_id', 'attributed_value']], on='target_id', how='left')

    for _, row in top_actors.iterrows():
        actor_name = row['actor_name'] or row['actor_id']
        actor_data = merged[merged['actor_id'] == row['actor_id']]
        for rev_type in rev_types:
            type_data = actor_data[actor_data['revenue_type'] == rev_type] if 'revenue_type' in actor_data.columns else actor_data
            if not type_data.empty:
                total_value = type_data['attributed_value'].sum() if 'attributed_value' in type_data.columns else type_data['value'].sum()
                if total_value > 0 and actor_name in node_indices and rev_type in node_indices:
                    sources.append(node_indices[actor_name])
                    targets_list.append(node_indices[rev_type])
                    values.append(total_value)
                    colors.append('rgba(16, 185, 129, 0.4)')

    if not sources:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient data for Sankey", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    # Node colors
    node_colors = []
    for node in nodes:
        if node in actor_types:
            node_colors.append('#3b82f6')
        elif node in rev_types:
            node_colors.append('#10b981')
        else:
            node_colors.append('#f59e0b')

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=[n.replace('_', ' ').title() for n in nodes],
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets_list,
            value=values,
            color=colors
        )
    )])

    fig.update_layout(
        title="Revenue Attribution Flow",
        template='plotly_white',
        height=500,
        font_size=12
    )

    return fig


def create_top_contributors_table(
    touchpoints_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    limit: int = 10
) -> pd.DataFrame:
    """
    Create a summary table of top contributors across all actor types.

    Args:
        touchpoints_df: DataFrame with columns: actor_type, actor_id, actor_name, target_id
        ledger_df: DataFrame with columns: target_id, attributed_value

    Returns:
        DataFrame with top contributors summary
    """
    if touchpoints_df.empty or ledger_df.empty:
        return pd.DataFrame(columns=['Actor Type', 'Name', 'Deals', 'Attributed Revenue'])

    # Merge and aggregate
    merged = touchpoints_df.merge(ledger_df, on='target_id', how='inner')

    summary = merged.groupby(['actor_type', 'actor_id', 'actor_name']).agg({
        'target_id': 'nunique',
        'attributed_value': 'sum'
    }).reset_index()

    summary.columns = ['Actor Type', 'Actor ID', 'Name', 'Deals', 'Attributed Revenue']
    summary['Actor Type'] = summary['Actor Type'].str.replace('_', ' ').str.title()
    summary['Name'] = summary['Name'].fillna(summary['Actor ID'])
    summary = summary.drop(columns=['Actor ID'])
    summary = summary.sort_values('Attributed Revenue', ascending=False).head(limit)

    return summary


def create_revenue_type_comparison_chart(targets_df: pd.DataFrame, touchpoints_df: pd.DataFrame) -> go.Figure:
    """
    Create a grouped bar chart comparing actor contributions by revenue type.

    Args:
        targets_df: DataFrame with columns: id, revenue_type, value
        touchpoints_df: DataFrame with columns: actor_type, target_id

    Returns:
        Plotly figure object
    """
    if targets_df.empty or touchpoints_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No comparison data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    # Merge and prepare comparison
    merged = touchpoints_df.merge(
        targets_df[['id', 'revenue_type', 'value']],
        left_on='target_id',
        right_on='id',
        how='inner'
    )

    if merged.empty or 'revenue_type' not in merged.columns:
        fig = go.Figure()
        fig.add_annotation(text="No revenue type data", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    # Fill missing revenue types
    merged['revenue_type'] = merged['revenue_type'].fillna('Unclassified')

    # Group by revenue type and actor type
    comparison = merged.groupby(['revenue_type', 'actor_type'])['value'].sum().reset_index()
    comparison_pivot = comparison.pivot(index='revenue_type', columns='actor_type', values='value').fillna(0)

    # Color mapping
    color_map = {
        'partner': '#3b82f6',
        'campaign': '#10b981',
        'sales_rep': '#f59e0b',
        'channel': '#8b5cf6',
        'customer_referral': '#ec4899',
        'event': '#06b6d4',
        'content': '#84cc16',
        'custom': '#6b7280'
    }

    fig = go.Figure()
    for col in comparison_pivot.columns:
        fig.add_trace(go.Bar(
            name=col.replace('_', ' ').title(),
            x=comparison_pivot.index.str.replace('_', ' ').str.title(),
            y=comparison_pivot[col],
            marker_color=color_map.get(col, '#6b7280'),
            text=comparison_pivot[col].apply(lambda x: f"${x:,.0f}" if x > 0 else ""),
            textposition='outside'
        ))

    fig.update_layout(
        title="Actor Contributions by Revenue Type",
        xaxis_title="Revenue Type",
        yaxis_title="Total Value ($)",
        barmode='group',
        template='plotly_white',
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig
