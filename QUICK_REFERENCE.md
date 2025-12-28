# Attribution MVP - Quick Reference Guide

## Quick Start

```bash
source .venv/bin/activate
streamlit run app.py
```

Navigate to `http://localhost:8501`

---

## Tab Overview

| Tab | Purpose | Key Features |
|-----|---------|--------------|
| **Dashboard** | Executive overview | Charts, metrics, exports |
| **Admin** | Configuration & bulk ops | Settings, rules, import/export |
| **Account Partner 360** | Relationship management | Link partners, view splits |
| **Account Drilldown** | Detailed account view | Revenue, attribution, explanations |
| **Relationship Summary** | AI insights | Summaries, recommendations |
| **Audit Trail** | Change history | Compliance, filtering, exports |

---

## Common Tasks

### View Key Metrics
1. Go to **Dashboard** tab
2. See 5 key metrics at top
3. Adjust time period (7, 30, 60, 90, 180 days)

### Export a Report
1. Navigate to desired tab
2. Scroll to export section
3. Choose format: CSV, Excel, or PDF
4. Click download button

### Import Data
1. Go to **Admin** tab
2. Scroll to "Bulk Import/Export"
3. Select **Import** sub-tab
4. Choose entity type
5. Upload CSV file
6. Click import button

### Link a Partner to Use Case
1. Go to **Account Partner 360** tab
2. Scroll to "Link partner to use case"
3. Select use case
4. Select partner
5. Optionally describe involvement
6. Click "Save"

### View Account Details
1. Go to **Account Drilldown** tab
2. Select account from dropdown
3. View use cases, partners, revenue, attribution
4. Export account report if needed

### Check Audit Trail
1. Go to **Audit Trail** tab
2. Set filters (time, event type, account)
3. Toggle "Show Details" for more info
4. Export if needed

### Configure Rules
1. Go to **Admin** tab
2. Scroll to "Attribution configuration"
3. Enable/disable use case or account rules
4. Add/modify rules as needed
5. Use "Rule impact simulator" to test

---

## Chart Types

### Dashboard Charts

1. **Revenue Over Time**: Line chart showing daily revenue trends
2. **Attribution Distribution**: Pie chart of revenue by partner
3. **Partner Performance**: Horizontal bar chart ranking partners
4. **Pipeline Funnel**: Deal stages and values
5. **Partner Role Distribution**: Donut chart of role types
6. **Attribution Waterfall**: Revenue flow visualization

All charts are interactive - hover for details!

---

## Export Formats

### CSV
- Simple, universal format
- Compatible with Excel, Google Sheets
- Single table per file

### Excel
- Multi-sheet workbooks
- Professional formatting
- Auto-width columns
- Color-coded headers

### PDF
- Publication-quality reports
- Executive summaries
- Multiple data tables
- Professional styling

---

## Keyboard Shortcuts

Streamlit default shortcuts:
- `R` - Rerun the app
- `Ctrl+C` (terminal) - Stop the server

---

## File Locations

### Configuration
- Database: `attribution.db`
- Logs: `attribution.log`
- Environment: `.env` (optional)

### Code Structure
```
attribution-mvp/
├── app.py                 # Main Streamlit app (6 tabs)
├── dashboards.py          # Visualization functions
├── exports.py             # Export utilities
├── bulk_operations.py     # Bulk import/export
├── db.py                  # Database operations
├── rules.py               # Rule engine
├── attribution.py         # Attribution logic
├── ai.py                  # AI features
├── models.py              # Data models
├── utils.py               # Utilities
├── config.py              # Configuration
└── tests/                 # Test suite
```

---

## Data Model Quick Reference

### Core Entities
- **Accounts**: Customer accounts
- **Partners**: Partner organizations
- **Use Cases**: Deals/opportunities
- **Use Case Partners**: Link between use case and partner
- **Account Partners**: Account-level split percentages

### Supporting Tables
- **Revenue Events**: Daily revenue data
- **Attribution Events**: Attribution ledger (who gets credit)
- **Attribution Explanations**: Detailed split explanations
- **Activities**: Activity log
- **Audit Trail**: Complete change history
- **Settings**: Application configuration

---

## Settings

### Key Configuration Options

**Enforce split cap**: Prevents total splits > 100% per account

**SI auto-split mode**:
- `live_share`: Based on use case value vs account totals
- `fixed_percent`: Use a set percentage
- `manual_only`: Always set manually

**Default splits**:
- Implementation (SI): Calculated dynamically or fixed
- Influence: 10%
- Referral: 15%
- ISV: 10%

---

## Troubleshooting

### Database Issues
```bash
# Reset database
rm attribution.db
streamlit run app.py  # Will recreate with demo data
```

### Import Errors
```bash
# Reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt
```

### Port Already in Use
```bash
# Use different port
streamlit run app.py --server.port 8502
```

### Charts Not Rendering
- Check browser console for errors
- Try refreshing the page (press `R`)
- Ensure plotly is installed: `pip list | grep plotly`

---

## Demo Tips

1. **Start with Dashboard**: Most impressive first view
2. **Show interactivity**: Hover over charts, change filters
3. **Download a report**: Demonstrates export capability
4. **Walk through one workflow**: e.g., linking a partner to use case
5. **Show audit trail**: Demonstrates transparency

---

## Support Resources

- `README.md` - Comprehensive documentation
- `DEMO_GUIDE.md` - Detailed demo script
- `TRANSFORMATION_SUMMARY.md` - Complete feature list
- `CHANGELOG.md` - Version history
- `AGENTS.md` - Development guidelines

---

## Quick Wins

### For a 5-Minute Demo
1. Show Dashboard (2 min)
2. Export one report (1 min)
3. Show audit trail (1 min)
4. Mention other capabilities (1 min)

### For a 15-Minute Demo
1. Dashboard (4 min)
2. Admin - bulk operations (3 min)
3. Account Partner 360 - link a partner (3 min)
4. Account Drilldown - detailed view (2 min)
5. Audit Trail (2 min)
6. Q&A (1 min)

### For a 30-Minute Deep Dive
- Walk through all 6 tabs
- Show rule configuration
- Demonstrate AI features
- Export multiple report types
- Discuss customization options

---

## Performance Tips

### For Better Performance
- Use date range filters to limit data
- Export large datasets to Excel for further analysis
- Use bulk operations for large imports
- Clear old audit trail entries periodically

### Typical Performance
- Dashboard load: < 2 seconds
- Chart rendering: < 1 second
- Excel export: < 3 seconds
- PDF generation: < 4 seconds

---

## Version Information

- **Current Version**: 2.0.0
- **Python**: 3.9+
- **Streamlit**: Latest
- **Database**: SQLite
- **Tests**: 29/29 passing (100%)

---

## Quick Command Reference

```bash
# Start app
streamlit run app.py

# Run tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html

# Install dependencies
pip install -r requirements.txt

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

---

## Contact & Support

For issues or questions:
1. Check this Quick Reference
2. Review DEMO_GUIDE.md
3. Check README.md
4. Review TRANSFORMATION_SUMMARY.md

---

**Last Updated**: 2025-12-27
**Document Version**: 2.0.0
