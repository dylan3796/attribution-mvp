# Attribution MVP - Demo Guide

This guide will walk you through a comprehensive demo of the Attribution MVP application, showcasing all major features and capabilities.

## Demo Script (15-20 minutes)

### Introduction (2 minutes)

**Overview**: The Attribution MVP is a partner attribution tracking system that automatically calculates revenue splits based on partner involvement and configurable business rules.

**Key Value Propositions**:
- Automated revenue attribution to partners
- Configurable rules engine
- AI-powered insights and recommendations
- Comprehensive audit trail
- Professional reporting and exports

---

### Tab 1: Dashboard (4 minutes)

**Navigate to**: Dashboard tab (first tab)

#### Key Metrics Section
Show the 5 key metrics at the top:
- Total Revenue
- Attributed Revenue (with coverage percentage)
- Active Accounts
- Partner Count
- Use Cases

**Talking Points**:
- "At a glance, we can see our entire attribution landscape"
- "The attribution coverage shows what percentage of revenue has been assigned to partners"

#### Interactive Charts
Walk through each chart:

1. **Revenue Over Time**
   - "This line chart shows daily revenue trends"
   - Hover over data points to show tooltips

2. **Attribution Distribution (Pie Chart)**
   - "This shows how revenue is distributed across partners"
   - "We can see which partners are driving the most value"

3. **Partner Performance Bar Chart**
   - "Horizontal bar chart ranks partners by attributed revenue"
   - "Colors indicate revenue levels for quick visual assessment"

4. **Pipeline Funnel**
   - "Shows pipeline value by stage (Discovery → Evaluation → Commit → Live)"
   - "Helps identify where deals are concentrated"

5. **Partner Role Distribution**
   - "Donut chart showing the mix of partner roles"
   - "Implementation partners vs Influence vs Referral vs ISV"

6. **Attribution Waterfall**
   - "Shows how total revenue flows to different partners"
   - "Identifies unattributed revenue"

#### Time Period Selector
- Change from "Last 30 days" to "Last 60 days" or "Last 90 days"
- Click "Refresh Dashboard" to update all charts

#### Export Capabilities
Show the export buttons:
- **Download Revenue CSV**: Raw revenue data
- **Download Attribution CSV**: Partner attribution data
- **Download Excel Report**: Multi-sheet workbook with all data
- **Download PDF Report**: Professional partner performance report

**Demo Action**: Download the Excel report and show the multi-sheet format with formatting.

---

### Tab 2: Admin (3 minutes)

**Navigate to**: Admin tab

#### Settings Configuration
Show the configuration options:
- **Enforce account split cap**: Toggle to control if splits must sum to ≤100%
- **SI auto-split mode**: Explain the three modes
  - `live_share`: Based on use case value vs account totals
  - `fixed_percent`: Use a set percentage
  - `manual_only`: Always set manually

#### Rule Engine
Scroll to "Attribution configuration":
- Show use case rules (gate link creation)
- Show account rules (control rollup to account splits)

**Talking Point**: "Rules give you complete control over which partners get attribution and under what circumstances"

#### Bulk Import/Export
Show the bulk operations section:
- **Import tab**: Upload CSV to bulk import accounts, partners, or use cases
- **Export tab**: Download complete data backup
- **Templates tab**: Download CSV templates

**Demo Action**: Download a CSV template to show the format.

---

### Tab 3: Account Partner 360 (3 minutes)

**Navigate to**: Account Partner 360 tab

#### Filtering
Show the three filter dropdowns:
- Filter by account
- Filter by stage
- Filter by partner

**Demo Action**: Select a specific account to filter the view.

#### Filtered Metrics
Point out how the metrics update based on filters:
- Accounts, Partners, Use Cases, AccountPartner links

#### Use Cases Table
- Shows all use cases with stage, estimated value, target close date
- Filtered based on selection

#### Link Partner to Use Case
Scroll to the form:
1. Select a use case
2. Select a partner
3. Optionally describe partner involvement
4. Click "Save use case ↔ partner (auto rollup)"

**Talking Points**:
- "The system uses AI to infer the partner role based on context"
- "It automatically calculates the appropriate split percentage"
- "Rules are evaluated to ensure compliance"

#### Partner Leaderboard
Scroll to the bottom:
- Shows partner impact over selected date range
- Includes accounts influenced, attributed revenue, active days
- Export to CSV button

---

### Tab 4: Account Drilldown (2 minutes)

**Navigate to**: Account Drilldown tab

Select an account from the dropdown.

#### Account Overview
Show the sections:
- **Use cases**: All deals for this account
- **AccountPartner links**: Partners engaged with this account
- **30d Account Revenue**: Total revenue
- **30d Attributed Revenue**: Revenue assigned to partners
- **Attributed revenue by partner**: Breakdown showing who gets credit

#### Attribution Explanations
- Click "Recompute explanations"
- Expand explanation entries to show:
  - Source (auto vs manual)
  - Split percentage
  - Reason for the split
  - Use case links
  - Rule decisions

#### Export Account Data
Show the export buttons:
- **Download Account Excel**: Multi-sheet report
- **Download Account PDF**: Professional account report

**Demo Action**: Download the PDF to show the polished report format.

---

### Tab 5: Relationship Summary (AI) (2 minutes)

**Navigate to**: Relationship Summary (AI) tab

Select an account.

#### Generate Summary
Click "Generate summary":
- System analyzes accounts, use cases, partners, activities
- Creates a concise 3-bullet summary
- Shows latest summary with timestamp

**Talking Points**:
- "AI summarizes complex relationships into actionable insights"
- "Works with or without OpenAI API key (uses intelligent fallback)"

#### Recent Activities
- Shows activity log for the account
- Tracks partner interactions and touchpoints

---

### Tab 6: Audit Trail (3 minutes)

**Navigate to**: Audit Trail tab

#### Filters
Show the filter options:
- **Time Period**: Select lookback window (7, 14, 30, 60, 90, 180, 365 days)
- **Event Type**: Filter by type of change
- **Account**: Filter by specific account
- **Show Details**: Toggle detailed view

#### Metrics
Point out the 4 metrics:
- Total Events
- Accounts Affected
- Partners Involved
- Event Types

#### Audit Trail Table
Show the table:
- Without details: Shows timestamp, event type, account, partner
- With details: Adds old value, new value, reason, actor

**Talking Point**: "Complete audit trail ensures transparency and compliance"

#### Export Audit Trail
Show export options:
- CSV
- Excel
- PDF report

---

### Advanced Features Demo (2 minutes)

#### Rule Impact Simulator (Admin tab)
Navigate back to Admin → scroll to "Rule impact simulator":
- Select "account_rules" or "use_case_rules"
- Set lookback days
- Click "Run simulation"
- Shows how many links would be allowed vs blocked
- Displays revenue at risk

**Talking Point**: "Test rule changes before applying them to see the impact"

#### AI Recommendations (Admin tab)
Scroll to "AI recommendations":
- Select an account
- Click "AI recommend attributions"
- System analyzes and suggests partner splits
- Click "Apply recommendations" to auto-update

---

## Key Demo Talking Points

### Business Value
- "Automates partner attribution, saving hours of manual work"
- "Ensures fair and consistent partner credit allocation"
- "Provides transparency with complete audit trail"
- "Generates professional reports for stakeholders"

### Technical Excellence
- "Production-grade architecture with modular design"
- "100% test coverage on core functionality"
- "Interactive visualizations for data exploration"
- "Flexible rule engine adapts to your business logic"

### Ease of Use
- "Intuitive UI with clear workflows"
- "Bulk import for easy migration"
- "Multiple export formats (CSV, Excel, PDF)"
- "AI-powered features reduce manual configuration"

---

## Demo Data Overview

The demo includes:
- **5 Accounts**: Enterprise customers
- **3 Partners**: Mix of Implementation, Influence, and Referral partners
- **6 Use Cases**: Deals across different stages
- **305 Revenue Events**: Daily revenue data
- **Complete Attribution**: All revenue attributed to partners

---

## Common Questions & Answers

**Q: Can I import my existing data?**
A: Yes! Use the Bulk Import feature in the Admin tab. Download CSV templates, fill them with your data, and upload.

**Q: What if my rules are complex?**
A: The rule engine supports combinations of role, stage, and deal size. You can also use natural language to create rules via the AI converter.

**Q: How does AI work without an API key?**
A: The system has intelligent fallbacks using heuristics and pattern matching. It works great out of the box, and even better with OpenAI.

**Q: Can I customize the split percentages?**
A: Absolutely! You can set default splits, configure auto-calculation rules, or manually override any split.

**Q: Is the audit trail comprehensive?**
A: Yes! Every change is logged with timestamp, actor, old/new values, and reason. Perfect for compliance.

---

## Demo Tips

1. **Start with Dashboard**: Immediately shows value with visualizations
2. **Use Real Scenarios**: "Imagine you're the partner operations manager..."
3. **Show Interactivity**: Click charts, change filters, download reports
4. **Highlight Automation**: Emphasize how much manual work this saves
5. **End with Export**: Leave them with a tangible PDF report they can review

---

## Follow-Up Actions

After the demo:
1. Provide download link or repository access
2. Share documentation (README, this guide)
3. Offer to walk through their specific use case
4. Discuss customization or integration options
5. Schedule follow-up for questions

---

## Success Metrics

A successful demo includes:
- Showed all 6 tabs
- Demonstrated at least 3 charts
- Exported at least 1 report (Excel or PDF)
- Explained the rule engine
- Displayed the audit trail
- Generated an AI summary or recommendation

Good luck with your demo!
