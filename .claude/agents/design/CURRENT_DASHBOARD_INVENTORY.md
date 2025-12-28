# Current Dashboard Inventory
**Date Documented:** 2025-12-28
**Purpose:** Preserve existing dashboard UI during backend rebuild

---

## App Structure

### Page Configuration
- **Page Title:** "Attribution MVP"
- **Layout:** Wide mode (`layout="wide"`)
- **Custom Styling:**
  - Gradient background: `#f5f7fa → #e8f0ff → #fdfbfb`
  - Rounded tabs with selected state styling (#d7e3ff background)
  - Metric cards with shadow and border styling
  - Custom padding and spacing

### Navigation Tabs (6 Total)
1. **Dashboard** - Executive overview with charts and metrics
2. **Admin** - Configuration and bulk operations
3. **Account Partner 360** - Relationship management
4. **Account Drilldown** - Detailed account view
5. **Relationship Summary (AI)** - AI-generated insights
6. **Audit Trail** - Change history and compliance

---

## Tab 0: Dashboard (PRIMARY TAB TO PRESERVE)

### Layout Structure
```
[Time Period Selector]  [Refresh Button]

[5 Metric Cards in Row]

---

### Revenue & Attribution Trends
[Revenue Over Time Chart]  [Attribution Pie Chart]

---

### Partner Performance & Pipeline
[Partner Performance Bar]  [Pipeline Funnel]

---

### Partner Insights
[Partner Role Distribution]  [Attribution Waterfall]

---

### Export Dashboard Data
[Download Revenue CSV]  [Download Attribution Excel]  [Download PDF Report]

---

### Top Partners Table
[Data Table: Top 10 Partners]
```

### Controls
- **Time Period Selector:**
  - Dropdown with options: 7, 30, 60, 90, 180 days
  - Default: 30 days
  - Format: "Last X days"
  - Component: `st.selectbox`

- **Refresh Button:**
  - Type: Primary button
  - Label: "Refresh Dashboard"
  - Component: `st.button`

### Key Metrics (5 Cards)

**Metric 1: Total Revenue**
- Value: `$XXX,XXX` (sum of revenue_events.amount for period)
- Delta: "Xd period" (dashboard_days)
- Component: `st.metric`

**Metric 2: Attributed Revenue**
- Value: `$XXX,XXX` (sum of attributed_amount)
- Delta: "XX.X% coverage" (attributed / total * 100)
- Component: `st.metric`

**Metric 3: Active Accounts**
- Value: Count of accounts
- Delta: "X with partners" (account_partners count)
- Component: `st.metric`

**Metric 4: Partner Count**
- Value: Total partners
- Delta: "X active" (partners with attributions)
- Component: `st.metric`

**Metric 5: Use Cases**
- Value: Total use cases
- Delta: "X live" (use_cases with stage='Live')
- Component: `st.metric`

### Charts (6 Total)

**Chart 1: Revenue Over Time**
- Type: Line chart with area fill
- Function: `create_revenue_over_time_chart(revenue_df)`
- Data: Daily revenue aggregated from revenue_events
- X-axis: revenue_date
- Y-axis: amount (sum)
- Features: Hover tooltips, zoom, pan
- Component: `st.plotly_chart`
- Color: Blue (#3b82f6) with light fill
- Key: "revenue_trend"

**Chart 2: Attribution Distribution**
- Type: Pie chart (donut with 40% hole)
- Function: `create_attribution_pie_chart(attribution_df)`
- Data: Attributed amount by partner
- Segments: partner_name
- Values: attributed_amount
- Features: Interactive legend, hover tooltips
- Component: `st.plotly_chart`
- Colors: Qualitative.Set3 palette
- Key: "attribution_pie"

**Chart 3: Partner Performance Leaderboard**
- Type: Horizontal bar chart
- Function: `create_partner_performance_bar_chart(attribution_df)`
- Data: Partners ranked by attributed revenue
- X-axis: attributed_amount
- Y-axis: partner_name
- Features: Color gradient (Blues), value labels
- Component: `st.plotly_chart`
- Sorted: Descending by attributed_amount
- Key: "partner_performance"

**Chart 4: Pipeline Funnel**
- Type: Funnel chart
- Function: `create_pipeline_funnel_chart(use_cases_df)`
- Data: Use cases by stage
- Stages: Discovery → Evaluation → Commit → Live
- Values: estimated_value (sum per stage)
- Features: Percent of initial stage shown
- Component: `st.plotly_chart`
- Colors: Green, Blue, Orange, Purple
- Key: "pipeline_funnel"

**Chart 5: Partner Role Distribution**
- Type: Donut chart (50% hole)
- Function: `create_partner_role_distribution(partner_roles_df)`
- Data: Count of partner roles
- Roles: Implementation (SI), Influence, Referral, ISV
- Values: Count of touchpoints per role
- Component: `st.plotly_chart`
- Colors: Blue, Green, Orange, Purple
- Key: "role_distribution"

**Chart 6: Attribution Waterfall**
- Type: Waterfall chart
- Function: `create_attribution_waterfall(attribution_df, total_revenue)`
- Data: Revenue flow from total → partners → unattributed
- Start: Total Revenue (purple)
- Decreasing: Partners (blue bars, subtracting attributed amounts)
- Final: Reconciled total
- Features: Connector lines, value labels
- Component: `st.plotly_chart`
- Key: "waterfall"

### Export Buttons (4 Total)

**Export 1: Revenue CSV**
- Label: "Download Revenue CSV"
- Function: `export_to_csv(revenue_df)`
- Filename: `revenue_{start_date}_to_{end_date}.csv`
- MIME: text/csv
- Component: `st.download_button`

**Export 2: Attribution Excel**
- Label: "Download Attribution Excel"
- Function: `export_to_excel({"Revenue": revenue_df, "Attribution": attribution_df})`
- Filename: `dashboard_{start_date}_to_{end_date}.xlsx`
- MIME: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- Multi-sheet workbook with formatting

**Export 3: PDF Report**
- Label: "Download PDF Report"
- Function: `create_partner_performance_report()`
- Filename: `partner_performance_report.pdf`
- MIME: application/pdf
- Executive summary + data tables

**Export 4: Top Partners CSV**
- Label: "Download Top Partners CSV"
- Function: `export_to_csv(top_10_df)`
- Filename: `top_partners_{start_date}_to_{end_date}.csv`
- MIME: text/csv

### Data Tables

**Top Partners Table**
- Title: "Top 10 Partners by Attributed Revenue"
- Columns:
  - partner_name
  - attributed_amount (formatted as currency)
  - avg_split_percent (formatted as percentage)
  - accounts_influenced (integer)
- Component: `st.dataframe`
- Features: Sortable, hoverable
- Limit: 10 rows

---

## Data Queries Used by Dashboard

### Revenue Data Query
```sql
SELECT revenue_date, amount, account_id
FROM revenue_events
WHERE revenue_date BETWEEN ? AND ?
ORDER BY revenue_date;
```

### Attribution Data Query
```sql
SELECT
    p.partner_name,
    p.partner_id,
    SUM(ae.attributed_amount) AS attributed_amount,
    AVG(ae.split_percent) AS avg_split_percent,
    COUNT(DISTINCT ae.account_id) AS accounts_influenced
FROM attribution_events ae
JOIN partners p ON p.partner_id = ae.actor_id
WHERE ae.revenue_date BETWEEN ? AND ?
GROUP BY p.partner_name, p.partner_id
ORDER BY attributed_amount DESC;
```

### Use Cases Data Query
```sql
SELECT use_case_id, use_case_name, stage, estimated_value, target_close_date, account_id
FROM use_cases
WHERE estimated_value IS NOT NULL;
```

### Partner Roles Data Query
```sql
SELECT partner_role, use_case_id, partner_id
FROM use_case_partners;
```

### Account Health Query
```sql
SELECT
    a.account_id,
    a.account_name,
    COUNT(DISTINCT u.use_case_id) AS active_use_cases,
    COUNT(DISTINCT ap.partner_id) AS total_partners,
    COALESCE(SUM(CASE WHEN u.stage = 'Live' THEN u.estimated_value ELSE 0 END), 0) AS live_value
FROM accounts a
LEFT JOIN use_cases u ON u.account_id = a.account_id
LEFT JOIN account_partners ap ON ap.account_id = a.account_id
GROUP BY a.account_id, a.account_name;
```

---

## Dependencies

### Visualization Functions (from dashboards.py)
- `create_revenue_over_time_chart(revenue_df)` - Line chart with area fill
- `create_partner_performance_bar_chart(attribution_df)` - Horizontal bar chart
- `create_attribution_pie_chart(attribution_df)` - Donut pie chart
- `create_pipeline_funnel_chart(use_cases_df)` - Funnel by stage
- `create_partner_role_distribution(partner_roles_df)` - Role donut chart
- `create_attribution_waterfall(attribution_df, total_revenue)` - Waterfall chart

### Export Functions (from exports.py)
- `export_to_csv(df, filename)` - CSV bytes
- `export_to_excel(sheets_dict)` - Multi-sheet Excel with formatting
- `create_partner_performance_report(partner_data, attribution_data, date_range)` - PDF report

### Libraries Used
- **Streamlit** - Web framework
- **Plotly** - Interactive charts
- **Pandas** - Data manipulation

---

## Color Scheme

### Chart Colors
- **Primary Blue:** #3b82f6 (revenue trends)
- **Green:** #10b981 (positive states, Discovery stage)
- **Orange:** #f59e0b (warnings, Commit stage)
- **Purple:** #8b5cf6 (totals, Live stage)
- **Blues Gradient:** Sequential palette for partner rankings
- **Qualitative Set3:** Multi-color palette for pie charts

### UI Colors
- **Selected Tab:** #d7e3ff (light blue)
- **Tab Border:** #b6ccff (blue)
- **Background Gradient:** #f5f7fa → #e8f0ff → #fdfbfb
- **Metric Cards:** White with light gray border (#e2e8f0)

---

## Responsive Behavior

### Column Layouts
- **Metrics Row:** 5 equal columns
- **Charts Row 1:** 2 equal columns (50/50 split)
- **Charts Row 2:** 2 equal columns (50/50 split)
- **Charts Row 3:** 2 equal columns (50/50 split)
- **Export Row:** 4 equal columns

### Chart Sizing
- All charts use `use_container_width=True`
- Default height varies by chart type:
  - Line charts: 400px
  - Pie charts: 400px
  - Bar charts: Dynamic (40px per partner, min 300px)
  - Funnel charts: 400px
  - Waterfall: 500px

---

## User Interactions

### Interactive Elements
1. **Time period selector** - Changes date range, re-runs all queries
2. **Refresh button** - Re-executes all dashboard queries
3. **Chart hovers** - Show tooltips with exact values
4. **Chart legends** - Click to hide/show series
5. **Export buttons** - Download data in various formats
6. **Data table sorting** - Click column headers to sort

### State Management
- Time period selection stored in local variable (not session state)
- Dashboard data loaded on demand (not cached)
- Ledger bootstrap flag in session state (`st.session_state["ledger_bootstrap"]`)

---

## Critical Requirements for New Architecture

### Must Support These Queries
The new AttributionLedger table MUST support equivalent queries that produce:
1. **Partner aggregations** (partner_id, SUM(attributed_amount), AVG(split_percent), COUNT(DISTINCT accounts))
2. **Time-series aggregations** (date, SUM(attributed_amount))
3. **Role distributions** (role, COUNT(*))
4. **Revenue totals** (SUM(revenue))

### Must Preserve These Components
1. **All 6 charts** - Exact same visual output
2. **All 5 metrics** - Same calculations
3. **Time period selector** - Same behavior
4. **Export buttons** - Same formats (CSV, Excel, PDF)
5. **Color scheme** - Same colors and gradients
6. **Layout structure** - Same column arrangements

### Can Refactor (But Output Must Match)
- Backend data models (as long as queries still work)
- Attribution calculation logic (as long as ledger entries match)
- Data ingestion pipeline (as long as data ends up in compatible format)

---

## Testing Checklist for Preservation

After rebuild, verify:
- [ ] Dashboard loads without errors
- [ ] All 5 metrics show correct values
- [ ] All 6 charts render correctly
- [ ] Time period selector changes date range
- [ ] Export buttons download files
- [ ] Charts are interactive (hover, legend, zoom)
- [ ] Color scheme matches original
- [ ] Layout is identical
- [ ] Performance is similar (<2s load time)

---

**End of Dashboard Inventory**
